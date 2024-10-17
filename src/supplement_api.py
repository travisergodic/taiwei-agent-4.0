

supplement_api_list = [
    {
        "name": "arithmetic",
        "description": "通过输入四则运算式字符串，输出计算结果。",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "需要传入的四则运算算式，例如，'(2.5 + 3.7 + 4.2)/3'"
                }
            },
            "required": ["expression"]
        },
        "paths": "src.supplement.arithmetic"
    }
]


def arithmetic(expression):
    try:
        expression = expression.replace("x", "*").replace("X", "*").replace("=", "").strip()
        return {"Result": eval(expression)}
    except:
        return {"Result": {}}


SUPPLEMET_API_NAMES = [api["name"] for api in supplement_api_list]