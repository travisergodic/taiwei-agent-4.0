import os
import json
import time
import logging

import qianfan

from src.prompt import *
from src.utils import function_request_yiyan, decode_json, json_to_markdown, split_indices_by_tokens, get_unique_function_call_indices, is_null_response, is_null_result_response
from src.api_wrapper import API_WRAPPER
from src.constants import AK, SK


logger = logging.getLogger(__name__)


class SplitAgent:
    def __init__(self, **kwargs):
        self.f = qianfan.ChatCompletion(ak=AK, sk=SK, **kwargs)
        
    def do(self, query):
        while True:
            try:
                content = SPLIT_MINIMAL_SOLVABLE_PROMPT_TEMPLATE.format(question=query)
                messages = [{"role": "user", "content": content}]
                response = self.f.do(messages=messages)
                res = response['body']['result'] 
                if res is None:
                    return 
                start_idx = res.find('[')
                end_idx = len(res) - res[::-1].find(']')
                return eval(res[start_idx: end_idx])
            except:
                logger.info(f"SplitAgent 输出不符合规范: {res}")
    

class SimpleCriticAgent:
    def __init__(self, **kwargs):
        self.f = qianfan.ChatCompletion(ak=AK, sk=SK, **kwargs)
    
    def do(self, query, answer):
        while True:
            content = CRITIC_USER_PROMPT.format(question=query, answer=answer)
            messages = [{"role": "user", "content": content}]
            response = self.f.do(
                messages=messages,
                top_p=0.1,
                temperature=0.1,
                system=CRITIC_SYSTEM_PROMPT
            )
            res = response['body']['result']
            if res.startswith("Y") and len(res) == 1:
                return True
            elif res.startswith("N") and len(res) == 1:
                return False


class SummaryAgent:
    def __init__(self, **kwargs):
        self.f = qianfan.ChatCompletion(ak=AK, sk=SK, **kwargs)

    def do(self, question, answers):
        answer_list = "\n".join(answers)
        content = SUMMARY_AGENT_USER_PROMPT.format(question=question, answer_list=answer_list)

        messages = [{"role": "user", "content": content}]
        response = self.f.do(
            messages=messages,
            top_p=0.1,
            system=SUMMARY_AGENT_SYSTEM_PROMPT,
            temperature=0.1
        )
        return response['body']['result']
    

class SolverAgent:
    def __init__(self, api_retry, api_helper=None, **kwargs):
        self.f_function = qianfan.ChatCompletion(ak=AK, sk=SK, **kwargs)
        self.f_summary = qianfan.ChatCompletion(model="ERNIE-4.0-8K-Latest", ak=AK, sk=SK)
        self.api_retry = api_retry
        self.api_helper = api_helper
        self.restart()

    def restart(self):
        self.messages = []
        self.api_list = None
        self.relevant_APIs = []
        self.return_list = []
        self.answer = None

    def __repr__(self):
        "Solver Agent"

    def do(self, query, retrieve_list, iteration, init_query=None):
        self.query = query
        solver_prompt = INITIAL_SOLVER_PROMPT.format(initial_question=query)
        url_list = [{"name": api["name"], "paths": api["paths"]} for api in retrieve_list]
        api_list = [{k: v for k, v in api.items() if k != "paths"} for api in retrieve_list]
        self.api_list = api_list

        self.messages = [{"role": "user", "content": solver_prompt}]
        n = 1
        while n <= iteration:
            try:
                res = function_request_yiyan(self.f_function, self.messages, api_list)
                response, func_name, kwargs = res["response"], res["func_name"], res["kwargs"]
            except Exception as e:
                if ("the max input characters" in str(e)) or ("Prompt tokens too long" in str(e)):
                    break
                logger.info(f"请求一言模型失败: {e}")
            
            if isinstance(response, str):
                self.answer = response
                self.messages += [{"role": "assistant", "content": self.answer}]
                break
            
            # 判断智能体回答
            try:
                next(item["paths"] for item in url_list if item["name"] == func_name)

            except StopIteration:
                logger.info(f"函数名称 {func_name} 不存在，重新调用函数!")
                n += 1
                continue
            
            # 打 API
            return_message = False
            action_input = kwargs # 初始參數為 kwargs
            self.api_helper.restart()
            for i in range(self.api_retry):
                api_wrapper = API_WRAPPER[func_name]
                # 打 API
                curr_relevant_api_list, curr_response_list = api_wrapper(func_name, action_input, self.query)
                curr_agent_name = "Solver agent" if i == 0 else "Helper agent"

                for relevant_api, curr_response in zip(curr_relevant_api_list, curr_response_list):
                    logger.info(f"{curr_agent_name} 调用函数：{relevant_api['api_name']}，参数：{relevant_api['required_parameters']}")
                    logger.info(f"函数返回：{curr_response}")

                # 失敗情境，有 API helper
                if all([is_null_response(ele) for ele in curr_response_list]):
                    # 不是最後一次 --> helper agent 重新產生 action_input
                    if i < (self.api_retry-1):
                        if init_query is None:
                            question = query
                        else:
                            question = f"{query}（原始问题：{init_query}）"
                        action_input = self.api_helper.do(
                            question=question,
                            action_name=func_name,
                            action_input=json.dumps(action_input, ensure_ascii=True)
                        )
                        if action_input is None:
                            continue
                        
                # 成功情境 --> 新增對話，新增 relevant APIs，退出
                else:
                    for relevant_api, curr_response in zip(curr_relevant_api_list, curr_response_list):
                        self.messages += [
                            {"role": "assistant", "content": f"Action: {func_name}\nAction Input: {relevant_api['required_parameters']}"},
                            {"role": "function", "content": json.dumps(curr_response, ensure_ascii=False)}
                        ]
                    self.relevant_APIs += curr_relevant_api_list
                    self.return_list += curr_response_list
                    return_message = True
                    break

            if not return_message:
                self.messages += [
                    {"role": "assistant", "content": f"Action: {func_name}\nAction Input: {kwargs}"}, # 使用原始的 kwargs
                    {"role": "function", "content": "暂时无法取得信息"}   
                ]
                self.relevant_APIs.append(
                    {"api_name": func_name, "required_parameters": kwargs}
                )
                self.return_list.append({"Result": {}})
            n+= 1
        return {"answer": self.answer, "relevant APIs": self.relevant_APIs, "messages": self.messages}
    
    def ernie4_summary(self):
        MAX_TOKEN = 19500

        # 移除重複的 API 調用
        unique_indices = range(len(self.relevant_APIs)) # get_unique_function_call_indices(self.relevant_APIs)
        self.relevant_APIs = [self.relevant_APIs[idx] for idx in unique_indices]
        self.return_list = [self.return_list[idx] for idx in unique_indices] 

        # 產生輸出不為空的 idx
        null_indices = [idx for idx, result in enumerate(self.return_list) if is_null_response(result)]
        not_null_indices = [idx for idx in range(len(self.return_list)) if idx not in null_indices]
        null_result_indices = [idx for idx, result in enumerate(self.return_list) if is_null_result_response(result)]

        # 產生輸出不為空的記錄
        not_null_relevant_apis = [self.relevant_APIs[idx] for idx in not_null_indices]
        not_null_return_list = [self.return_list[idx] for idx in not_null_indices]

        # 產生 relevant_api 的 doc
        relevant_api_names = set([api["api_name"] for api in not_null_relevant_apis])
        api_doc = json_to_markdown([api for api in self.api_list if api["name"] in relevant_api_names])

        chunk_indices_list = split_indices_by_tokens(
            relevant_apis=not_null_relevant_apis,
            observations=not_null_return_list,
            max_tokens=MAX_TOKEN
        )

        # 最終回傳的函數調用記錄 & 返回結果 & 答案
        final_relevant_apis, final_relevant_responses, final_answers = [], [], []

        for chunk_indices in chunk_indices_list:
            record_str = ""
            for k, idx in enumerate(chunk_indices):
                api, observation = not_null_relevant_apis[idx], not_null_return_list[idx]
                record_str += f"{k+1}. 函数名称：{api['api_name']}, 函数参数：{json.dumps(api['required_parameters'], ensure_ascii=False)}, 返回结果：{json.dumps(observation, ensure_ascii=False)}\n"

            content = GIVE_ANSWER_PROMPT.format(
                question=self.query,
                api_list=api_doc,
                records=record_str
            )
            curr_relevant_apis = [not_null_relevant_apis[idx] for idx in chunk_indices]
            curr_relevant_responses = [not_null_return_list[idx] for idx in chunk_indices]

            decode_success = False
            for i in range(3):
                try:
                    time.sleep(1)
                    response = self.f_summary.do(
                        messages=[{"role": "user", "content": content}],
                        top_p=0.1,
                        temperature=0.1
                    )
                    raw = response["result"]
                    res = decode_json(raw)
                    answer = res["answer"]
                    relevant_indices = res["relevant_numbers"]
                    decode_success = True
                    break

                except Exception as e:
                    logger.info(f"ernie4_summary 解碼錯誤：{e}")

            if not decode_success:
                continue

            try:
                final_relevant_apis += [curr_relevant_apis[int(ele)-1] for ele in relevant_indices]
                final_relevant_responses += [curr_relevant_responses[int(ele)-1] for ele in relevant_indices]
                final_answers.append(answer)
            except:
                final_relevant_apis += curr_relevant_apis
                final_relevant_responses += curr_relevant_responses
                final_answers.append(answer)

        TARGET_API = ["ticket_info_query"]
        null_result_responses = [self.return_list[idx] for idx in null_result_indices] 
        null_result_relevant_apis = [self.relevant_APIs[idx] for idx in null_result_indices]
        null_result_relevant_apis = [ele for ele in null_result_relevant_apis if ele["api_name"] in TARGET_API]
        
        null_result_unique_indices = get_unique_function_call_indices(null_result_relevant_apis)
        # final_relevant_apis += [null_result_relevant_apis[idx] for idx in null_result_unique_indices]
        # final_relevant_responses += [null_result_responses[idx] for idx in null_result_unique_indices]

        logger.info(f"\nrelevant response: {final_relevant_responses}\n")
        return final_answers, final_relevant_apis # + null_result_relevant_apis


class ComplexCriticAgent:
    def __init__(self, max_retry, **kwargs):
        self.f = qianfan.ChatCompletion(ak=AK, sk=SK, **kwargs)
        self.max_retry = max_retry
    
    def do(self, query, answer_list):
        for _ in range(self.max_retry):
            content = EXTRACT_UNSOLVED_QUESTION_USER_PROMPT.format(question=query, answer_list="\n".join(answer_list))
            messages = [{"role": "user", "content": content}]
            time.sleep(1)
            response = self.f.do(
                messages=messages,
                top_p=0.1,
                temperature=0.1,
                system=EXTRACT_UNSOLVED_QUESTION_SYSTEM_PROMPT,
                response_format="json_object"
            )
            raw= response['body']['result']
            try:
                res = decode_json(raw)
                if res["is_success"].startswith("Y"):
                    return True, res["unsolved_query"]
                if res["is_success"].startswith("N"):
                    return False, res["unsolved_query"]
                
            except Exception as e:
                logger.info(f"Complex Critic 解码错误: {e}")
                time.sleep(1)
        return None, None
    

class APIHelper:
    def __init__(self, api_list, max_retry, **kwargs):
        self.f = qianfan.ChatCompletion(ak=AK, sk=SK, **kwargs)
        self.api_list = api_list
        self.max_retry = max_retry
        self.restart()

    def restart(self):
        self.messages = []

    def __repr__(self):
        "Helper Agent"

    def do(self, question, action_name, action_input):
        # 找出函數對應的 document
        for i, api_doc in enumerate(self.api_list):
            if api_doc["name"] == action_name:
                api_idx = i
                break

        # if self.messages:
        #     content = API_HELPER_ERROR_RETRY_PROMPT
        # else:
        content = API_HELPER_USER_PROMPT_TEMPLATE.format(
            question=question,
            action_input=json.dumps(action_input, ensure_ascii=False),
            action_params_doc=api_doc["parameters"]["properties"]
        )
        self.messages += [{"role": "user", "content": content}]

        for i in range(self.max_retry):
            time.sleep(1)
            try:
                response = self.f.do(
                    messages=self.messages,
                    top_p=0.5,
                    temperature=0.5
                )
                raw = response['body']['result']
            except Exception as e:
                continue
            try:
                res = decode_json(raw)
                all_keys = self.api_list[api_idx]["parameters"]["properties"].keys()
                required_keys = self.api_list[api_idx]["parameters"]["required"]
                # remove useless keys
                res = {k:v for k, v in res.items() if k in all_keys}

                # check all required keys exist
                if not all([rk in res for rk in required_keys]):
                    continue

                if not isinstance(res, dict):
                    continue
                return res
                
            except Exception as e:
                logger.info(f"API helper 解码错误: {e}")
        return None