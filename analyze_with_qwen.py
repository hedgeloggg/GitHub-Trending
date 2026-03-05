import os
from http import HTTPStatus
import dashscope

dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

def analyze_projects(projects):
    prompt = "你是一位资深技术专家，请用中文简洁说明以下 GitHub 项目的用途、核心技术与适用场景（每个项目不超过 80 字）：\n"
    for p in projects:
        prompt += f"- {p['name']}: {p['description']}\n"
    
    response = dashscope.Generation.call(
        model="qwen-max",
        prompt=prompt,
        max_tokens=1000
    )
    if response.status_code == HTTPStatus.OK:
        return response.output.text
    else:
        raise Exception(f"Qwen API error: {response.code} - {response.message}")
