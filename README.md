# 百度搜索·文心智能体创新大赛”技术赛道：基于多工具调用的开放域问答智能体构建
![alt text](assets/competition.png)
## [竞赛链结](https://aistudio.baidu.com/competition/detail/1235/0/introduction)
## 团队信息
1. **队名**：初级程序员的团队
2. **队员**：胡太维（队长）
3. **初赛名次**：7 / 1008
4. **决赛名次**：8 / 30 (优胜奖🥇)

## 比賽概述
通过调用百度 AI Studio 49 个 API 回答用户问题（API 列表详见 `data/api_list.json`），范例如下：
```bash
USER: 计划2024年9月5日从无锡自驾去上海旅游，想了解当天无锡的92号油价、当天上海是否有限号、上海的道路拥堵情况。另外计划在上海市长宁区虹桥街道兴义路48号新世纪广场B座1层的荣新馆和位于上海市黄浦区西藏南路237号新尚数码广场6楼的上海1号私藏菜餐厅用餐，它们的日常营业时间是什么。

AGENT: 2024年9月5日无锡的92号油价为7.63元/升，上海没有限行，上海的道路拥堵指数为1.28，状态为畅通。荣新馆的日常营业时间为11:15-13:30和17:15-21:30，上海1号私藏菜餐厅的日常营业时间为11:00-14:00和17:00-21:00。

USER: 2024年9月7号，香港迪士尼和上海迪士尼哪个更贵？哪个地方最低温度更高？同时，帮我找到上海迪士尼乐园和东方明珠的封面照片的链接，并比较这两个地方的门票价格。

AGENT: 
1. 2024年9月7号，香港迪士尼的门票价格更贵。
2. 2024年9月7号，上海的最低温度更高。
3. 上海迪士尼乐园的封面照片链接为：https://dimg04.c-ctrip.com/images/1lo4y12000fyl6vvq7787_C_500_280.jpg。
4. 东方明珠的封面照片链接为：https://dimg04.c-ctrip.com/images/010691200097uy8rk36FE_C_500_280.jpg。
5. 上海迪士尼乐园和东方明珠的门票价格分别为￥399起和￥199起，上海迪士尼乐园的门票价格更高。

...
```

## 架构图
![alt text](assets/agent_system.png)

## 安装
```bash
pip install -r requirements.txt
```

## 百度千帆 Token
请改写 `src/constants.py` 中的 `AK` 与 `SK`

## 使用方法
```bash
python tools/inference_re.py --config_file config/taiwei-agent.yaml \
                             --dataset dataset.json \
                             --topk 5 \
                             --save_path result.json \
                             --max_iter 10 8 8 7
```
+ `config_file`：配置文件。
+ `dataset`：问题集的 JSON 档路径。
+ `topk`：每一轮 LLM retriever 最多提取的工具个数。
+ `save_path`：系统回答结果的 JSON 档储存路径。
+ `max_iter`：每一轮的对话次数。以 `10 8 8 7` 为例，表示共有 4 轮对话，每轮对话的次数分别为 `10, 8, 8, 7`。