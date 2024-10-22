import re
import os
import time
import logging

import qianfan
import paddle
from dotenv import load_dotenv
# from paddlenlp.transformers import AutoModel, AutoTokenizer

from src.prompt import RECOMMEND_PROMPT
from src.constants import AK, SK


logger = logging.getLogger(__name__)


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
        reg_retrieve_list, tools_to_keyword = self.match_tool_by_reg(query)

        if exclude_indices is None:
            curr_api_list = self.api_list
        else:
            curr_api_list = [api for idx, api in enumerate(self.api_list) if idx not in exclude_indices]

        content = RECOMMEND_PROMPT.format(
            question=query, 
            api_list="\n".join([f"名称：{api['name']}，描述：{api['description']}" for api in curr_api_list]),
            topk=topk
        )

        for retry in range(6):
            f = self.f1 if retry < 3 else self.f2
            if retry > 0: 
                time.sleep(1)
            response = f.do(
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
                break
        
        # 按照先後順序
        llm_retrieve_list = llm_retrieve_list[:topk]
        llm_retrieve_set = set()
        new_llm_retrieve_list = []
        for tool in llm_retrieve_list:
            if (tool in llm_retrieve_set) or (tool in reg_retrieve_list):
                continue
            new_llm_retrieve_list.append(tool)
            llm_retrieve_set.add(tool)
        return (reg_retrieve_list + new_llm_retrieve_list), tools_to_keyword
    
    def match_tool_by_reg(self, query):
        tool_indices = []
        tools_to_keyword = dict()
        for reg, indices in self.reg_to_idices.items():
            match = re.search(reg, query)
            if match:
                tool_indices += indices
                keyword = match.group(0)
                tools_to_keyword[tuple([self.api_list[i]["name"] for i in indices])] = keyword
        return list(set(tool_indices)), tools_to_keyword