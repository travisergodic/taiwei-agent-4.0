import os
import time
import json
import yaml
import logging

import qianfan
from src.prompt import BRIEF_SUMMARY_PROMPT
from src.constants import AK, SK


logger = logging.getLogger(__name__)


# def function_request_yiyan(f, msgs, func_list):
#     """
#     发送请求到一言大模型，获取返回结果。

#     Args:
#         f: 一言API的访问对象。
#         msgs: 请求消息列表.
#         func_list: 请求中需要调用的API列表。
    
#     Returns:
#         返回值为一个包含三个元素的元组:
#         - response: 一言大模型返回的响应结果。
#         - func_name: 响应结果中调用的函数名，为str类型。
#         - kwargs: 响应结果中调用的函数的参数，为dict类型。
    
#     """
#     response = f.do(
#         messages=msgs,
#         functions=func_list, 
#     )
#     time.sleep(1)
#     if response['body']['result']:
#         return {
#             "response": response['body']['result'], 
#             "func_name": "", 
#             "kwargs": ""
#         }
#     func_call_result = response["function_call"]
#     func_name = func_call_result["name"]

#     try:
#         kwargs = eval(func_call_result["arguments"])
#     except:
#         corrected_str = func_call_result["arguments"].replace("'", '"')
#         kwargs = json.loads(corrected_str)

#     res = {
#         "response": response, 
#         "func_name": func_name, 
#         "kwargs": kwargs
#     }
#     if "thoughts" in func_call_result:
#         res["thoughts"] = func_call_result["thoughts"]
#     return res


def function_request_yiyan(f, msgs, func_list):
    """
    发送请求到一言大模型，获取返回结果。

    Args:
        f: 一言API的访问对象。
        msgs: 请求消息列表.
        func_list: 请求中需要调用的API列表。
    
    Returns:
        返回值为一个包含三个元素的元组:
        - response: 一言大模型返回的响应结果。
        - func_name: 响应结果中调用的函数名，为str类型。
        - kwargs: 响应结果中调用的函数的参数，为dict类型。
    
    """
    time.sleep(1)
    response = f.do(
        messages=msgs,
        functions=func_list, 
    )
    if response['body']['result']:
        return {
            "response": response['body']['result'], 
            "func_name": "", 
            "kwargs": ""
        }
    
    func_call_result = response["function_call"]
    func_name = func_call_result["name"]

    try:
        kwargs = json.loads(func_call_result["arguments"])
    except json.JSONDecodeError:
        corrected_str = func_call_result["arguments"].replace("'", '"')
        kwargs = json.loads(corrected_str)

    res = {
        "response": response, 
        "func_name": func_name, 
        "kwargs": kwargs
    }
    
    if "thoughts" in func_call_result:
        res["thoughts"] = func_call_result["thoughts"]
    return res


def load_yaml(path):
    with open(path, "r") as f:
        config = yaml.safe_load(f)
    return config


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        res = json.load(f)
    return res

def load_api_list():
    with open("data/api_list.json", "r", encoding="utf-8") as f:
        api_list = [json.loads(line) for line in f.readlines()]
    return api_list

def load_api_list_refine():
    with open("data/api_list_refine.json", "r", encoding="utf-8") as f:
        api_list = [json.loads(line) for line in f.readlines()]
    return api_list

def load_reg_to_tools():
    with open("data/reg_to_tools.json", "r", encoding="utf-8") as f:
        reg_to_tools = json.load(f)
    return reg_to_tools


def find_matching_bracket(input_string):
    # Initialize variables to track bracket count and index
    bracket_count = 0
    first_bracket_index = -1
    corresponding_closing_bracket_index = -1

    # Loop through the string to find the matching closing bracket
    for i, char in enumerate(input_string):
        if char == '{':
            if bracket_count == 0:
                first_bracket_index = i
            bracket_count += 1
        elif char == '}':
            bracket_count -= 1
            if bracket_count == 0 and first_bracket_index != -1:
                corresponding_closing_bracket_index = i
                break

    return first_bracket_index, corresponding_closing_bracket_index


def decode_json(raw):
    start, end = find_matching_bracket(raw)
    raw = raw[start:end+1]
    try:
        return json.loads(raw)
    except:
        try:
            return eval(raw)
        except:
            pass

    raw = raw.replace("'", '"')
    try:
        return json.loads(raw)
    except:
        return eval(raw)


def json_to_markdown(json_docs):
    # Helper function to process a single function's JSON document into Markdown
    def process_function_doc(func_data):
        # Extract name and description
        name = func_data.get("name", "Unnamed Function")
        description = func_data.get("description", "No description available.")

        # Extract parameters
        parameters = func_data.get("parameters", {}).get("properties", {})
        required_params = func_data.get("parameters", {}).get("required", [])

        # Construct markdown string
        markdown = f"### {name}\n"
        markdown += f"**描述**: {description}\n"
        markdown += "**参数**:\n"

        for param_name, param_info in parameters.items():
            is_required = "必填" if param_name in required_params else ""
            param_type = param_info.get("type", "string")
            param_description = param_info.get("description", "No description available.")
            markdown += f"- `{param_name}` ({param_type}, {is_required}): {param_description}\n"

        return markdown

    # Process all function documents
    markdown_docs = [process_function_doc(doc) for doc in json_docs]
    
    # Join all markdown documents into a single string
    return "\n".join(markdown_docs)


def split_indices_by_tokens(relevant_apis, observations, max_tokens=20000):
    chunks = []
    current_chunk = []
    current_tokens = 0
    api_observation_pairs = list(zip(relevant_apis, observations))

    for i, (api, observation) in enumerate(api_observation_pairs):
        # 生成当前记录的字符串
        record = f"函数名称：{api['api_name']}, 函数参数：{json.dumps(api['required_parameters'], ensure_ascii=False)}, 返回结果：{json.dumps(observation, ensure_ascii=False)}\n"
        
        # 计算当前记录的 token 数量
        record_tokens = len(record)
        
        # 如果加上当前记录会超出最大 token 数，则保存当前 chunk，并开启新 chunk
        if current_tokens + record_tokens > max_tokens:
            chunks.append(current_chunk)  # 保存当前 chunk 的索引
            current_chunk = []  # 重置 current_chunk
            current_tokens = 0  # 重置 token 计数器
        
        # 添加当前记录的索引到 current_chunk
        current_chunk.append(i)
        current_tokens += record_tokens

    # 添加最后一个 chunk
    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def get_unique_function_call_indices(function_call_list):
    seen = set()  # To keep track of seen (api_name, required_parameters) pairs
    unique_indices = []
    
    for idx, item in enumerate(function_call_list):
        # Convert the 'required_parameters' dictionary to a tuple of sorted key-value pairs
        params_tuple = tuple(sorted(item['required_parameters'].items()))
        params_tuple = tuple((ele[0], str(ele[1])) for ele in params_tuple)
        # Create a unique identifier for the function call
        identifier = (item['api_name'], params_tuple)
        
        # If this identifier hasn't been seen before, add the index to the result list
        if identifier not in seen:
            seen.add(identifier)
            unique_indices.append(idx)
    return unique_indices


def is_null_response(func_response):
    if func_response == "error：404":
        return True
    
    if len(func_response) == 0:
        return True
    
    if (list(func_response.keys()) == ["Result"]) and len(func_response["Result"]) == 0:
        return True
    
    if ("data" in func_response):
        if not func_response["data"]:
            return True
    
    # if "data" in func_response:
    #     data = func_response["data"]
    #     if not data:
    #         return True
        
    return False


def is_null_result_response(func_response):    
    if (list(func_response.keys()) == ["Result"]) and len(func_response["Result"]) == 0:
        return True    
    return False


def make_brief_response(question, api, params, response_str):
    content = BRIEF_SUMMARY_PROMPT.format(
        question=question, 
        api=api,
        params=json.dumps(params, ensure_ascii=False),
        response=response_str
    )
    f = qianfan.ChatCompletion(model="ERNIE-4.0-8K-Latest", ak=AK, sk=SK)
    for i in range(3):
        try:
            time.sleep(1)
            response = f.do(
                messages=[{"role": "user", "content": content}],
                top_p=0.1,
                temperature=0.1
            )
            raw = response["result"]
            res = decode_json(raw)
            brief_response = res["brief_response"]
            return {"Result": brief_response}

        except Exception as e:
            logger.info(f"ernie4_summary 解碼錯誤：{e}")
    return {"Result": {}}
    
