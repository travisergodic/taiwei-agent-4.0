import re
import os
import time

import qianfan
import paddle
from dotenv import load_dotenv
# from paddlenlp.transformers import AutoModel, AutoTokenizer

from src.prompt import RECOMMEND_PROMPT

load_dotenv()
AK = os.getenv("AK")
SK = os.getenv("SK")


class Retriever:
    def __init__(self, api_list, reg_to_tools, **kwargs):
        self.api_list = api_list
        self.tool_to_idx = {api["name"]:idx for idx, api in enumerate(api_list)}
        self.reg_to_idices = {
            reg:[self.tool_to_idx[tool] for tool in tools] \
                for reg, tools in reg_to_tools.items()
            } 
        self.f1 = qianfan.ChatCompletion(model="ERNIE-functions-8K", ak=AK, sk=SK, **kwargs)
        self.f2 = qianfan.ChatCompletion(model="ERNIE-4.0-8K", ak=AK, sk=SK, **kwargs)

    def retrieve(self, query, topk, exclude_indices=None):
        reg_retrieve_list = self.match_tool_by_reg(query)

        if exclude_indices is None:
            curr_api_list = self.api_list
        else:
            curr_api_list = [api for idx, api in enumerate(self.api_list) if idx not in exclude_indices]

        content = RECOMMEND_PROMPT.format(
            question=query, 
            api_list="\n".join([f"名称：{api['name']}，描述：{api['description']}" for api in curr_api_list]),
            topk=topk
        )

        for retry in range(3): 
            time.sleep(1)
            response = self.f1.do(
                messages=[{"role": "user", "content": content}],
                top_p=0.3,
                temperature=0.3,
            )
            llm_retrieve_list = []

            for i, ele in enumerate(self.api_list):
                name = ele["name"]
                if name in response["result"]:
                    llm_retrieve_list.append(i)

            if len(llm_retrieve_list) <= topk and len(llm_retrieve_list) >= 1:
                return list(set(llm_retrieve_list + reg_retrieve_list))
        
        for retry in range(3): 
            time.sleep(1)
            response = self.f2.do(
                messages=[{"role": "user", "content": content}],
                top_p=0.3,
                temperature=0.3,
            )
            llm_retrieve_list = []

            for i, ele in enumerate(self.api_list):
                name = ele["name"]
                if name in response["result"]:
                    llm_retrieve_list.append(i)

            if len(llm_retrieve_list) <= topk and len(llm_retrieve_list) >= 1:
                return list(set(llm_retrieve_list + reg_retrieve_list))
        return list(set(llm_retrieve_list + reg_retrieve_list))
    
    def match_tool_by_reg(self, query):
        tool_indices = []
        for reg, indices in self.reg_to_idices.items():
            if re.search(reg, query):
                tool_indices += indices
        return list(set(tool_indices))