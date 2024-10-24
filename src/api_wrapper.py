import re
import json
import requests
from copy import deepcopy
import datetime
import logging


from src.registry import Register
from src.utils import load_api_list, is_null_response, is_null_result_response, make_brief_response
import src.supplement_api


logger = logging.getLogger(__name__)


name_to_paths = {api["name"]:api["paths"] for api in load_api_list()}
name_to_api = {api["name"]:{k:v for k, v in api.items() if k != "paths"} for api in load_api_list()}


def truncate_json(data, num_token):
    return json.dumps(data, ensure_ascii=False)[:num_token]


def is_valid_date_format(date_str):
    # Regular expressions for "xx年xx月xx日" and "xx月xx日" formats
    full_date_pattern = r"^\d{1,4}年\d{1,2}月\d{1,2}[号日]$"
    month_day_pattern = r"^\d{1,2}月\d{1,2}[号日]$"
    
    # Check if the input matches either of the two patterns
    if re.match(full_date_pattern, date_str) or re.match(month_day_pattern, date_str):
        return True
    else:
        return False
    

def get_date_list(date_range_text):
    # 检查输入是否为"X月X号到X月X号"形式
    month_day_pattern = re.match(r'(\d+)月(\d+)[号日]到(\d+)月(\d+)[号日]', date_range_text)
    
    if month_day_pattern:
        start_month, start_day, end_month, end_day = map(int, month_day_pattern.groups())
        start_date = datetime.datetime(datetime.datetime.now().year, start_month, start_day)
        end_date = datetime.datetime(datetime.datetime.now().year, end_month, end_day)
        
        date_list = []
        current_date = start_date
        
        while current_date <= end_date:
            date_list.append(f"{current_date.month}月{current_date.day}日")
            current_date += datetime.timedelta(days=1)
        
        return date_list
    
    # 检查输入是否为"YYYY年X月到YYYY年X月"形式
    year_month_pattern = re.match(r'(\d+)年(\d+)月到(\d+)年(\d+)月', date_range_text)
    
    if year_month_pattern:
        start_year, start_month, end_year, end_month = map(int, year_month_pattern.groups())
        
        date_list = []
        current_year = start_year
        current_month = start_month
        
        while current_year < end_year or (current_year == end_year and current_month <= end_month):
            date_list.append(f"{current_year}年{current_month}月")
            if current_month == 12:
                current_month = 1
                current_year += 1
            else:
                current_month += 1
                
        return date_list
    return None


def convert_date_to_weekday(date_string):
    try:
        date = convert_date_string_to_data_object(date_string)    
        weekday = date.strftime('%A')  # Get the weekday name in English
        weekday_map = {
            'Monday': '周一',
            'Tuesday': '周二',
            'Wednesday': '周三',
            'Thursday': '周四',
            'Friday': '周五',
            'Saturday': '周六',
            'Sunday': '周日'
        }
        return weekday_map[weekday]
    except Exception as e:
        return None


def convert_date_string_to_data_object(date_string):
    # Define regex pattern to match 'x年x月x日'
    pattern_with_year = r'(\d{1,4})年(\d{1,2})月(\d{1,2})[号日]'
    pattern_without_year = r'(\d{1,2})月(\d{1,2})[号日]'
    
    # Search for the date in the string
    match_with_year = re.search(pattern_with_year, date_string)
    match_without_year = re.search(pattern_without_year, date_string)

    if match_with_year:
        year = int(match_with_year.group(1))
        month = int(match_with_year.group(2))
        day = int(match_with_year.group(3))

    elif match_without_year:
        year = datetime.datetime.now().year
        month = int(match_without_year.group(1))
        day = int(match_without_year.group(2))
    try:
        return datetime.date(year, month, day)
    except Exception as e:
        return None


def convert_date_to_month(date_string):
    # Define regex patterns to match both 'x月x號' or 'x月x日' and 'x年x月x號' or 'x年x月x日'
    pattern_with_year = r'(\d{1,4})年(\d{1,2})月(\d{1,2})[号日]'
    pattern_without_year = r'(\d{1,2})月(\d{1,2})[号日]'

    # Check for the pattern with year first
    match_with_year = re.search(pattern_with_year, date_string)
    if match_with_year:
        year = int(match_with_year.group(1))
        month = int(match_with_year.group(2))
        return f'{year}年{month}月'
    
    # If no match, check for the pattern without year
    match_without_year = re.search(pattern_without_year, date_string)
    if match_without_year:
        month = int(match_without_year.group(1))
        return f'{month}月'
    return None


def default_api_wrapper(api_name, params, question):
    try:        
        if api_name in src.supplement_api.supplement_api_list:
            return eval(f"src.supplement_api.{api_name}")(**params)
        else:
            url = "http://match-meg-search-agent-api.cloud-to-idc.aistudio.internal" + name_to_paths[api_name]
            response = requests.get(url, params=params).json()
            # 工具返回结果过长，做截断处理
            if len(str(response)) > 2500:
                response_str = truncate_json(response, 2500)
                return [{"api_name": api_name, "required_parameters": params}], [{"Result": response_str}]

    except Exception as e:
        logger.info(f"response error: {e}")
        # response = "error：404"
        response = {"Result": {}}
    return [{"api_name": api_name, "required_parameters": params}], [response]


API_WRAPPER = Register('api_wrapper', default=default_api_wrapper)


@API_WRAPPER.register("bd_gov_xianxing")
def bd_gov_xianxing_api(api_name, params, question):
    url = "http://match-meg-search-agent-api.cloud-to-idc.aistudio.internal" + name_to_paths[api_name]
    try:
        date = params["date_or_day_of_week"]
        if not is_valid_date_format(date):
            raise ValueError("Invalid date format")
        weekday = convert_date_to_weekday(date)
        if weekday is None:
            response = {"Result": {}}
        else:
            params["date_or_day_of_week"] = weekday
            params["city"] = params["city"].strip("市")
            response = requests.get(url, params=params).json()
            # 沒有限行
            if is_null_result_response(response):
                response = {"Result": f"{date}{params['city']}没有限行"}
            # 找不到結果
            elif is_null_response(response):
                return response
            # 找到結果
            else:
                response["supplement"] = f"{date}为{weekday}"
    except Exception as e:
        logger.info(f"response error: {e}")
        response = {}
    return [{"api_name": api_name, "required_parameters": params}], [response]


@API_WRAPPER.register("baidu_muti_weather")
def baidu_muti_weather_api(api_name, params, question):
    url = "http://match-meg-search-agent-api.cloud-to-idc.aistudio.internal" + name_to_paths[api_name]
    try:
        curr_relevant_api_list, curr_response_list = [], []
        month = convert_date_to_month(params["period"])
        if month is None:
            response = requests.get(url, params=params).json()
            curr_relevant_api_list.append({"api_name": api_name, "required_parameters": params})
            curr_response_list.append(response)
        else:
            date_string = params["period"]
            date = convert_date_string_to_data_object(date_string)
            for period in [f"{month}底", f"{month}中旬", f"{month}上旬"]:
                params["period"] = period
                response = requests.get(url, params=params).json()
                start_date = datetime.date(*[int(ele) for ele in response["Result"]["start_date"].strip().split("-")])
                end_date = datetime.date(*[int(ele) for ele in response["Result"]["end_date"].strip().split("-")])
                if (start_date <= date) and (date <= end_date):
                    curr_relevant_api_list.append({"api_name": api_name, "required_parameters": deepcopy(params)})
                    curr_response_list.append(response)
                    break
                
            if not is_null_response(response):
                response["Result"]["supplement"] = f"无法直接提供单一日期温度信息，{date_string}為{period}"  # f"请使用{period}的温度、体感信息代表 {date_string}"
                # response["Result"].pop("start_date")
                # response["Result"].pop("end_date")
                # response["Result"]["date"] = date_string
        return curr_relevant_api_list, curr_response_list

    except Exception as e:
        logger.info(f"response error: {e}")
        # response = "error：404"
        response = {"Result": {}}
    return [{"api_name": api_name, "required_parameters": params}], [response]


@API_WRAPPER.register("baidu_fule_price")
def baidu_fule_price_api(api_name, params, question):
    url = "http://match-meg-search-agent-api.cloud-to-idc.aistudio.internal" + name_to_paths[api_name]
    try:
        curr_relevant_api_list, curr_response_list = [], []

        date_list = get_date_list(params["date"])
        if date_list is None:
            response = requests.get(url, params=params).json()
            curr_relevant_api_list.append({"api_name": api_name, "required_parameters": params})
            curr_response_list.append(response)
        else:
            for date in date_list:
                params["date"] = date
                response = requests.get(url, params=params).json()
                curr_relevant_api_list.append({"api_name": api_name, "required_parameters": deepcopy(params)})
                curr_response_list.append(response)
        return curr_relevant_api_list, curr_response_list
    
    except Exception as e:
        logger.info(f"response error: {e}")
        return [{"api_name": api_name, "required_parameters": params}], [{"Result": {}}]
    

@API_WRAPPER.register("ticket_info_query")
def ticket_info_query_api(api_name, params, question):
    url = "http://match-meg-search-agent-api.cloud-to-idc.aistudio.internal" + name_to_paths[api_name]
    travel_mode = params["travel_mode"]
    all_travel_mode_list = ("火车", "高铁", "城际", "动车", "飞机", "汽车")
    try:
        curr_relevant_api_list, curr_response_list = [], []
        if travel_mode == "全部":
            for travel_mode in all_travel_mode_list:
                params["travel_mode"] = travel_mode
                response = requests.get(url, params=params).json()
                curr_relevant_api_list.append({"api_name": api_name, "required_parameters": deepcopy(params)})
                curr_response_list.append(response)
        else:
            response = requests.get(url, params=params).json()
            if not is_null_response(response) and ("date" in response["Result"]):
                response["Result"].pop("date")

            curr_relevant_api_list.append({"api_name": api_name, "required_parameters": params})
            curr_response_list.append(response)
        return curr_relevant_api_list, curr_response_list
    
    except Exception as e:
        logger.info(f"response error: {e}")
        return [{"api_name": api_name, "required_parameters": params}], [{"Result": {}}]