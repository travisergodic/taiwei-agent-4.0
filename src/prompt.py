# SPLIT_MINIMAL_SOLVABLE_PROMPT_TEMPLATE = """
# 请将以下问句拆解成若干个最小可解问题，并输出为 list of strings 的形式，例如："['问题一', '问题二', '问题三']"。（请注意：输出只需包含问题的文字，不要有其他说明或格式，请确保每个问题都是可以被解决的）

# {question}
# """

SPLIT_MINIMAL_SOLVABLE_PROMPT_TEMPLATE = """
用户问题：{question}

用户问题可能包含多个子问题，请将用户问题进行拆解，并遵循以下规则：
1. 每个拆解后的问题必须包含完整信息，并且能够单独解决。
2. 所有拆解后的问题必须涵盖原始问题的所有内容。
3. 如果问题无法拆解，则直接返回原始问题。
4. 拆解后的问句务必要通顺，允许在含义不变的情况下，改写原本的子问题。

请以 JSON 格式返回，并包含以下字段：
- `queries`: 一个包含拆解后问题的列表，例如：["问题一", "问题二", "问题三"]

除此之外，不要提供任何其他解释或说明。
"""

CRITIC_SYSTEM_PROMPT = """
你是一个能够检查回答句是否完全解答提问句中所有问题的助手。你的任务是判断回答句是否充分解决提问句的所有问题。只回传一个词："Y" 表示完整，"N" 表示不完整。
"""

CRITIC_USER_PROMPT="""
提问句：
{question}

回答句：
{answer}
"""

INITIAL_SOLVER_PROMPT = "[1. 若部分问题无法立即解决，请先解决其他部分 2. 若部分工具无法解决当下问题，请尝试其他工具] {initial_question}"
# FOLLOW_UP_SOLVER_PROMPT = "[1. 若部分问题无法立即解决，请先解决其他部分 2. 若部分工具无法解决当下问题，请尝试其他工具] {follow_up_question}（问题来源：{initial_question}）"

FOLLOW_UP_SOLVER_PROMPT = """{follow_up_question}

补充信息（仅供参考，无需处理）：
1. 注意事项：
   + 若部分问题无法立即解决，请先处理可解决部分。
   + 若某个工具无法解决当前问题，请尝试其他工具。
2. 问题来源：
{initial_question}
3. 相关信息：
{relevant_infos}
"""


EXTRACT_UNSOLVED_QUESTION_USER_PROMPT="""
提问句：
{question}

回答句：
{answer}
"""


EXTRACT_UNSOLVED_QUESTION_SYSTEM_PROMPT = """
你的任务是判断当前搜集的信息是否充分解决用户提问中的所有问题。若存在未解答的问题，生成一个新的提问句，涵盖所有 用户提问未解决的问题。请遵循以下规则：
1. 依据当前信息与提问进行判断
   + 只基于当前提供的信息和用户提问判断问题是否已解决，避免主观推测或分析。
2. 判断未解决的问题
   + 若用户提问中的部分或全部问题未得到明确解答，视为未解决。
   + 若信息对问题有所回应，但回答不明确或表明暂时无法回答，也视为未解决。
3. 生成简洁的后续提问
   + 新提问句必须简明扼要，包含所有未解决的子问题，并确保新提问句是完整且可解的。
   + 新提问句不得长于原用户提问句的长度。
4. 不得生成原问题之外的新问题。
5. 输出格式
   + 结果必须以 JSON 格式返回，包含以下两个字段：
     + is_success：若所有问题均已解答，值为 Y；否则为 N。
     + unsolved_query：若 is_success 为 N，则提供生成的提问句；若为 Y，则为空字符串 ""。
"""


EXTRACT_UNSOLVED_QUESTION_USER_PROMPT = """
提问句：
{question}

当前信息：
{answer_list}
"""


# API_HELPER_SYSTEM_PROMPT = """
# 你是 API helper agent，专门负责检查和修正 solver agent 传入的函数参数。每次接收到 solver agent 调用 API 并失败的情况，你需要根据 API 的 document (以 JSON 格式提供) 来检查 solver agent 提供的函数参数，并输出修正后的参数。你需要理解 API 的需求，确保所有必填参数存在且格式正确，并输出修正后的函数参数。

# 你将收到：
# 1. solver agent 试图解决的问题描述
# 2. solver agent 调用的 API 函数名称
# 3. solver agent 提供的函数参数 (JSON 格式)
# 4. API 的 document (JSON 格式)
# 5. solver agent 的函数调用失败信息

# 你的任务是分析失败原因，修正参数，并返回包含两个 key 的 JSON：
# 1. `error_description`：描述此次调用失败的原因
# 2. `corrected_parameters`：修正后的函数参数。若没有参数要输入，请以 "{}" 表示，例如
# 请确保输出严格为 JSON 格式，不允许额外的文字解释或注释。任何补充信息只能包含在 JSON 的 `error_description` 中，且格式必须完全符合 JSON 规范。
# """

# API_HELPER_SYSTEM_PROMPT = """
# 你是 API helper agent，负责修正函数参数。每次 solver agent 调用 API 因部分参数格式传入失败时，你需要根据提供的 API 文档（JSON 格式）检查并修正参数，确保必填项存在且格式正确。

# 你将收到：
# 1. solver agent 试图解决的问题描述
# 2. solver agent 调用的 API 函数名称
# 3. solver agent 提供的函数参数 (JSON 格式)
# 4. API 文档 (JSON 格式)

# 你的工作要求：
# 1. 保持意图一致性：你的修正必须保留 solver agent 原本的意图，不应修改参数的核心含义或范围。
# 2. 参数修正规则：只修正传入格式错误的参数，传入格式正确的参数不需要改动，确保参数符合 API 文档要求。
# 3. 不扩展范围：不要添加 solver agent 未提供的额外信息，除非是 API 文档的必填项。

# 你的输出要求：
# + 返回 JSON，且只包含 `corrected_parameters` 一个 key，表示修正后的参数，格式如下：
#   ```json
#   {"corrected_parameters": {"location": "青岛", "period": "2024年10月1日"}}
#   ```
# + 如果函数不需要传参，返回 `{"corrected_parameters": {}}`。

# 不要提供解释或分析错误原因，只需返回修正后的参数。
# """



# API_HELPER_USER_PROMPT_TEMPLATE = """
# solver agent 调用的函数名称：{action_name}
# solver agent 提供的函数参数：{action_input}
# 函数的 API 文档：{api_doc}
# solver agent 正在解决的问题：{question}
# """


API_HELPER_USER_PROMPT_TEMPLATE = """
函数 func 的参数规范如下：

{action_params_doc}

在解决 "{question}" 问题时，我调用了函数 func，并使用了 {action_input} 作为参数。由于部分参数格式不正确，调用失败。请参考参数规范，修正传入的参数格式，但请保持参数的原始含义：
1. 格式正确的参数请保持不变。
2. 对于信息不完整的参数，可参考问题描述中的相关内容，但不要尝试直接解决问题。
3. 只需返回修正后的参数，无需解释或分析错误原因。

输出要求：
1. 以 JSON 格式直接返回修正后的参数。
2. 不要添加额外解释。
"""

API_HELPER_ERROR_RETRY_PROMPT="""
函数调用依然失败，请再做尝试。
"""


# RECOMMEND_PROMPT = """

# 请推荐 API 列表中前 5 个最适合解决 "{question}" 的 API 名称，并直接输出名称，不要输出其他信息，格式范例：['API 名称一', 'API 名称一', ...]（注意：你的目标不是直接回答问题，而是推荐合适的 API 工具）

# API 列表：
# {api_list}
# """


RECOMMEND_PROMPT = """
用户问题：{question}

工具列表：
{api_list}

请推荐工具列表中适合解决用户问题的**工具名称**，并遵循以下原则：
1. 不要有自己的主观判断、也不要试图回答用户的问题，你的任务是推荐适合解决用户问题的工具。
2. 最多返回 {topk} 个适合解决用户问题的工具名称，并返回不少於 2 个工具。
3. 确保推荐的所有工具能解决用户提出的所有问题。
4. 不要有其他解释，或其他不相关的描述。

请以 list of string 格式回传工具名称，例如：[工具名称一, 工具名称一, ...]
"""




SELF_REFLECTION_PROMPT = """
请问你是否还有未解决的问题（包含当下无法得知的信息或遗漏的信息）？请以 JSON 格式输出，输出必须遵循以下规范：

输出的 JSON 必须包含 `is_success` 与 `following_question` 两个 key
1. `is_success`：若判断所有问题已被解决，输出 Y；否则，输出 N
2. `following_question`：若 `is_success` 为 Y，直接输出空字串 ""；否则，以问句形式输出未解决问题 
"""

self_reflection_func_list = [
   {
   "name": "return_result",
   "description": "回传结果给下一轮的 Agent。",
   "parameters": {
      "type": "object",
      "properties": {
         "is_success": {
         "type": "string",
         "description": "'Y' 表示所有问题都已完整解决或回答，'N' 表示仍有未解决问题或遗漏的回答，未解决的问题包括当下无法回答的内容、需要更多信息才能回答的情况，或部分问题的回答存在遗漏。"
         },
         "following_question": {
         "type": "string",
         "description": "如果 is_success 为 'N'，这里将包含未解决的问题或遗漏的信息，具体可能包括：1. 当前无法提供的答案；2. 需要更多信息才能回答的部分；3. 回答中被遗漏或尚未回答的问题。如果 is_success 为 'Y'，则返回空字符串。"
         }
      },
      "required": ["is_success", "following_question"]
   }
   }
]


SUMMARY_AGENT_SYSTEM_PROMPT="""
你负责根据使用者的提问与当前提供的信息进行回复。你必须遵循以下原则：

1. 简短回复：只提供与问题有关的信息，避免冗长或不相关的内容。
2. 事实为基础：严格基于提供的当前信息进行回答，杜绝主观判断或推测。
3. 选择最能解决问题的信息：如果有多则信息与问题中的某个子问题相关，选择最能解决该子问题的信息来回复，切勿对同个子问题有两种不同的说法。
4. 处理不足信息：如果某部分问题无法直接回答，但有与该部分问题相关信息，请简短提供这些信息；若完全没有相关信息，请明确表示 "无法获取相关信息"。

范例：
#### 问题：
请问 2024 年 10 月 1 日上海平均气温几度？从上海开车去扬州，最短多长时间？

#### 当前信息：
- 2024 年 10 月 1 日从上海开车去扬州约 2 小时，无法取得当天气温信息
- 2024 年 10 月 1 日上海气温约 25 度

#### 回复：
2024 年 10 月 1 日上海气温约 25 度，开车去扬州约 2 小时
"""


SUMMARY_AGENT_USER_PROMPT="""
提问句：
{question}

当前信息：
{answer_list}
"""


RETRIVER_CRITIC_USER_PROMPT = """
用户问题如下：
{question}

现在你有以下这几个工具：

{api_list}


请问这些工具是否可以解决用户**所有**的问题？请以 JSON 格式输出，并包含以下字段：
1. `solvable`: Y 或 N。Y 表示所有问题都可以被解决，N 表示有部分或全部问题无法被解决。
2. `useful_tool`: 对解决问题有帮助的工具名称，以 list of string 格式输出工具的名称。
"""


PLANNER_PROMPT_TEMPLATE = """
用户问题如下：
{question}

现在你有以下这几个工具：

{api_list}


你的任务是调用这些工具来解决用户所有问题，请根据执行顺序条列使用工具的名称与对应传入的参数。解题时，请遵循以下几个原则：
1. 不要试图去解决用户的问题，也不要根据自己主观的判断进行回答。
2. 尽量选择能直接解决用户问题的工具。

请回传 JSON 格式，并包含以下字段：
1. `function`：依序会调用的函数名称，以 list of string 格式进行回传。
2. `kwargs`：依序会传入的函数参数，必须要与 `function` 的顺序保持一致，以 list of dictionary 格式进行回传，如果某函数不需要传入参数，请以 empty dictionary 代表，**务必确保所有必要参数 (required) 都有传入函数中**。

除此之外，请不要有其他解释或说明。
"""

FOLLOWUP_PLANNER_PROMPT_TEMPLATE = """
以下是你调用函数时，传参的结果：
{error_list}

传参时，你存在一些错误，请详阅这些工具的使用法与用户的问题，重新回传更正后的结果。

请回传 JSON 格式，并包含以下字段：
1. `function`：依序会调用的函数名称，以 list of string 格式进行回传。
2. `kwargs`：依序会传入的函数参数，必须要与 `function` 的顺序保持一致，以 list of dictionary 格式进行回传，如果某函数不需要传入参数，请以 empty dictionary 代表，**务必确保所有必要参数 (required) 都有传入函数中**。

除此之外，请不要有其他解释或说明。
"""



GIVE_ANSWER_PROMPT = """
用户问题如下：
{question}

现在有以下这几个工具：
{api_list}


以下是我调用的工具、传入的参数与函数返回结果：
{records}


请帮我根据函数返回的信息**对用户的问题进行回答**，并返回**回答所依据的函数返回结果编号**，回复时必须遵守以下规则：
1. 简短回复：根据当前信息，不要加入不相关的内容。
2. 事实为基础：根据提供的当前信息进行回答，不得加入主观判断或猜测。
3. 精准匹配：从当前信息中筛选与问题最相关的事实。如果有多个事实与问题相关，选择最能解决问题且最可信的信息来回复。
4. 简单算术：若需要通过算术操作得出答案，请执行必要的计算。
5. 处理不足信息：如果某部分问题无法直接回答，但有与该部分问题相关信息，请简短提供这些信息；若完全没有相关信息，请明确表示 "无法获取相关信息"。

请回传 JSON 格式，并包含以下字段：
1. `answer`：对用户问题的回复，以 string 格式进行回传。
2. `relevant_numbers`：回复用户问题所依据的函数返回结果编号，以 list of integer 格式进行回传，如果没有依据任何函数返回结果，请以 empty list 代表。
"""

SELF_REFLECTION_ANSWER_PROMPT = """
请重新检视原始问题、你之前的回复答案与前几轮函数回传的结果，再生成一次答案，并遵循以下原则：
1. 如果发现你之前的回复答案与函数调用结果不一致，请做修正。
2. 如果发现当前搜集的信息可以回复问题的某些部分，但你却没有回复，请回復。
3. 正确的回复部分请不要更改。
4. 请直接输出回复的答案给，不要有其他解释或说明。
"""


HUMAN_GUIDE_PROMPT = """
我有以下問題的解決方案：
{question_list}

請問有哪些問題能解決或部分解決用戶問題：{curr_question}

请回传 JSON 格式，并包含以下字段：
1. `can_solve`：若能解決全部或部分用戶問題，值为 Y；否则为 N。
2. `relevant_questions`：以 list of integer 格式进行回传，若 `can_solve` 為 N，直接輸出 empty list；否則，以列表形式輸出能解決全部或部分用戶問題的編號。
"""

RETRIVER_PROMPT_TEMPLATE = """
用户提问：{question}

以下是所有工具的类别：
{label_list}

请回传解决用户提问的所有工具类别。
"""