import os
import sys
import json
import argparse
sys.path.insert(0, os.getcwd())

from src.utils import load_yaml, load_api_list, load_json, get_unique_function_call_indices, load_reg_to_tools, load_api_list_refine
from src.retrieve import Retriever
from src.prompt import INITIAL_SOLVER_PROMPT, FOLLOW_UP_SOLVER_PROMPT
from src.agent import ComplexCriticAgent, SummaryAgent, SolverAgent, APIHelper


def main():
    api_list = load_api_list()
    api_list_refine = load_api_list_refine()
    reg_to_tools = load_reg_to_tools()
    records = load_json(args.dataset)
    print(f"共 {len(api_list)} 支 API")

    if args.q_indices:
        records = [records[idx] for idx in args.q_indices]

    # 負責提取重要的 API
    retriever = Retriever(api_list=api_list_refine, reg_to_tools=reg_to_tools)
    
    # 評判回答是否正確
    critic_agent = ComplexCriticAgent(**config["CRITIC"])

    # 對回答進行統整
    summary_agent = SummaryAgent(**config["SUMMARY"])
    
    # 負責修正 action input
    api_helper = APIHelper(api_list, **config["API_HELPER"])

    # 負責解決問題
    solver_agent = SolverAgent(api_helper=api_helper, **config["SOLVER"])

    for record in records:
        qid = record["qid"]
        query = record["query"]

        print(f"({qid}) 用户query：{query}")

        curr_query = query
        answer_list, relevant_apis = [], []
        for i in range(args.max_iter):
            solver_agent.restart()

            if not args.manual_retrive:
                retrive_idxs = retriever.retrieve(curr_query, args.topk)
            else:
                retrive_idxs = args.manual_retrive

            retrieve_list = [api_list[idx] for idx in retrive_idxs]
            print(f"提取 API：{[ele['name'] for ele in retrieve_list]}")
            if len(retrieve_list) == 0:
                break
            
            if i == 0:
                solver_prompt = INITIAL_SOLVER_PROMPT.format(initial_question=curr_query)
            else:
                solver_prompt = FOLLOW_UP_SOLVER_PROMPT.format(follow_up_question=curr_query, initial_question=query)
            
            solver_agent.do(solver_prompt, retrieve_list)
            curr_answer_list, curr_relevant_apis = solver_agent.ernie4_summary()
            print("relevant_APIs:", curr_relevant_apis)
            
            # solver agent 未給出答案
            if len(curr_answer_list) == 0:
                print("Solver Agent：此轮未给出答案")
                continue
            else:
                print(f"Solver Agent 给出答案：{curr_answer_list}")
                
            # solver agent 給出答案
            answer_list += curr_answer_list
            relevant_apis += curr_relevant_apis

            if i < (args.max_iter-1):
                # 判斷是否全部回答
                is_success, curr_query = critic_agent.do(curr_query, answer_list)

                if is_success == True:
                    print(f"Complex Critic 评估问题已解决，退出循环")
                elif is_success == False:
                    print(f"Complex Critic 提出后续问题：{curr_query}")
                else: # is_succes == None
                    continue

                if is_success:
                    break

        # > 1 個以上回答，用 summary agent 做集成
        if len(answer_list) > 1:
            print("answer_list:", answer_list)
            final_answer = summary_agent.do(query, answer_list)

        # ==1 直接是答案
        elif len(answer_list) == 1:
            final_answer = answer_list[0] 

        # relevant api 去重
        relevant_apis_indices = get_unique_function_call_indices(relevant_apis)
        relevant_apis =[relevant_apis[idx] for idx in relevant_apis_indices]

        if len(answer_list) >= 1:            
            reply = {
                "query": query, "query_id": qid, 
                "result": final_answer, "relevant APIs": relevant_apis
            }
            print(f"最终答案：{final_answer}")
            
        else:
            reply = {
                "query": query, "query_id": qid, 
                "result": "抱歉，无法回答此问题。", "relevant APIs": relevant_apis
            }
            print("抱歉，无法回答此问题。")
        
        with open(args.save_path, "a", encoding='utf-8') as f:
            f.write(json.dumps(reply, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inference")
    parser.add_argument("--config_file", type=str, required=True)
    parser.add_argument("--dataset", type=str, required=True)
    parser.add_argument("--q_indices", nargs='+', type=int)
    parser.add_argument("--topk", type=int, required=True)
    parser.add_argument("--save_path", type=str, required=True)
    parser.add_argument("--max_iter", type=int, required=True)
    parser.add_argument("--manual_retrive", nargs='+', type=int, default=[])
    parser.add_argument("--retriever_critic", action="store_true")
    args = parser.parse_args()
    config = load_yaml(args.config_file)
    main()