import os
from http import HTTPStatus
import dashscope

dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

def analyze_projects(projects):
    prompt = (
        "你是一位资深开发者，请为以下 GitHub 项目生成简洁中文说明（每项不超过 100 字）。\n"
        "请严格按以下格式输出，每个项目占两行：\n"
        "【项目名】\n"
        "用途与亮点...\n\n"
        "项目列表：\n"
)
for p in projects:
    prompt += f"- {p['name']} ({p['link']}): {p['description']}\n"
    
    response = dashscope.Generation.call(
        model="qwen-max",
        prompt=prompt,
        max_tokens=1000
    )
    if response.status_code == HTTPStatus.OK:
        return response.output.text
    else:
        raise Exception(f"Qwen API error: {response.code} - {response.message}")
