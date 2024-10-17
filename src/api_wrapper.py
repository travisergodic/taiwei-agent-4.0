import re
import json
import requests
from copy import deepcopy
from datetime import datetime, timedelta

from src.registry import Register
from src.utils import load_api_list
import src.supplement_api


name_to_paths = {api["name"]:api["path"] for api in load_api_list()}


def truncate_json(data, num_token):
    return {"Result": json.dumps(data, ensure_ascii=False)[:num_token]}


def get_date_list(date_range_text):
    # 检查输入是否为"X月X号到X月X号"形式
    month_day_pattern = re.match(r'(\d+)月(\d+)日到(\d+)月(\d+)日', date_range_text)
    
    if month_day_pattern:
        start_month, start_day, end_month, end_day = map(int, month_day_pattern.groups())
        start_date = datetime(datetime.now().year, start_month, start_day)
        end_date = datetime(datetime.now().year, end_month, end_day)
        
        date_list = []
        current_date = start_date
        
        while current_date <= end_date:
            date_list.append(f"{current_date.month}月{current_date.day}日")
            current_date += timedelta(days=1)
        
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


def convert_date_to_period(date_string):
    # Define regex patterns to match dates in 'x月x號' or 'x月x日' format
    pattern = r'(\d{1,2})月(\d{1,2})[号日]'
    
    # Search for the date in the string
    match = re.search(pattern, date_string)
    if match:
        month = int(match.group(1))
        day = int(match.group(2))
        
        # Determine which period the day falls into
        if 1 <= day <= 10:
            period = '上旬'
        elif 11 <= day <= 20:
            period = '中旬'
        else:
            period = '月底'
        
        return f'{month}月{period}'
    return date_string


def default_api_wrapper(api_name, params):
    try:        
        if api_name in src.supplement_api.supplement_api_list:
            return eval(f"src.supplement_api.{api_name}")(**params)
        else:
            url = "http://match-meg-search-agent-api.cloud-to-idc.aistudio.internal" + name_to_paths[api_name]
            response = requests.get(url, params=params).json()
            # 工具返回结果过长，做截断处理
            if len(str(response)) > 1500:
                response = truncate_json(response, 1500)        
    except Exception as e:
        print(f"response error: {e}")
        # response = "error：404"
        response = {"Result": {}}
    return [{"api_name": api_name, "required_parameters": params}], [response]


API_WRAPPER = Register('api_wrapper', default=default_api_wrapper)


@API_WRAPPER.register("baidu_muti_weather")
def baidu_muti_weather_api(api_name, params):
    url = "http://match-meg-search-agent-api.cloud-to-idc.aistudio.internal" + name_to_paths[api_name]
    try:
        params["period"] = convert_date_to_period(params["period"])
        response = requests.get(url, params=params).json()

    except Exception as e:
        print(f"response error: {e}")
        # response = "error：404"
        response = {"Result": {}}
    return [{"api_name": "baidu_muti_weather", "required_parameters": params}], [response]


@API_WRAPPER.register("baidu_fule_price")
def baidu_fule_price_api(api_name, params):
    url = "http://match-meg-search-agent-api.cloud-to-idc.aistudio.internal" + name_to_paths[api_name]
    try:
        curr_relevant_api_list, curr_response_list = [], []
        if "到" not in params["date"]:
            params["date"] = f'{params["date"]}到{params["date"]}' 

        date_list = get_date_list(params["date"])
        for date in date_list:
            params["date"] = date
            response = requests.get(url, params=params).json()
            curr_relevant_api_list.append({"api_name": "baidu_fule_price", "required_parameters": deepcopy(params)})
            curr_response_list.append(response)
        return curr_relevant_api_list, curr_response_list
    
    except Exception as e:
        print(f"response error: {e}")
        return [{"api_name": "baidu_fule_price", "required_parameters": params}], [{"Result": {}}]