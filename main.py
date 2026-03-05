# main.py
import os
import sys
import requests
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
import smtplib
from http import HTTPStatus
import time
import traceback

# ========== 配置 ==========
# 从环境变量读取（GitHub Secrets）
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
EMAIL_USER = os.getenv("EMAIL_USER")        # 发件人邮箱（如 xxx@gmail.com）
EMAIL_PASS = os.getenv("EMAIL_PASS")        # 应用专用密码或授权码
TO_EMAIL = os.getenv("TO_EMAIL")            # 收件人邮箱
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")  # 默认 Gmail
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))           # 默认 SSL 端口

# ========== 工具函数 ==========
def fetch_github_trending():
    print("🔍 正在抓取 GitHub 今日热门项目...")
    url = "https://github.com/trending?since=daily"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; GitHub Trending Digest Bot)"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"❌ 抓取失败: {e}")
        return []

    soup = BeautifulSoup(resp.text, 'html.parser')
    repos = []
    for article in soup.select('article'):
        name_tag = article.select_one('h2 a')
        if not name_tag:
            continue
        name = ''.join(name_tag.stripped_strings).replace(' ', '')
        link = "https://github.com" + name_tag['href']
        desc_tag = article.select_one('p')
        description = desc_tag.get_text(strip=True) if desc_tag else ""
        repos.append({"name": name, "link": link, "description": description})
        if len(repos) >= 10:
            break
    print(f"✅ 成功获取 {len(repos)} 个项目")
    return repos

def analyze_with_qwen(projects):
    print("🧠 正在调用 Qwen-Max 分析项目...")
    if not DASHSCOPE_API_KEY:
        raise ValueError("DASHSCOPE_API_KEY 未设置！请在 Secrets 中配置。")

    prompt = (
    "你是一位资深开发者，请为以下 GitHub 项目生成简洁中文说明（每项不超过 100 字），"
    "格式严格按：\n"
    "- 【项目名】用途与亮点...\n\n"
    "项目列表：\n"
    )
    for p in projects:
    prompt += f"- {p['name']} ({p['link']}): {p['description']}\n"

    try:
        from dashscope import Generation
        response = Generation.call(
            model="qwen-max",
            prompt=prompt,
            api_key=DASHSCOPE_API_KEY,
            max_tokens=1000
        )
        if response.status_code == HTTPStatus.OK:
            return response.output.text
        else:
            raise RuntimeError(f"Qwen API 错误: {response.code} - {response.message}")
    except Exception as e:
        print(f"⚠️ Qwen 分析失败，使用原始描述代替: {e}")
        fallback = "\n".join([
            f"- {p['name']}: {p['description'] or '无描述'}"
            for p in projects
        ])
        return "（Qwen 分析失败，显示原始信息）\n\n" + fallback

def send_email(subject, body):
    print("📧 正在发送邮件...")
    if not all([EMAIL_USER, EMAIL_PASS, TO_EMAIL]):
        raise ValueError("邮箱配置缺失！请检查 EMAIL_USER, EMAIL_PASS, TO_EMAIL Secrets。")

    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = EMAIL_USER
    msg['To'] = TO_EMAIL

    try:
        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=15)
        else:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15)
            server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, [TO_EMAIL], msg.as_string())
        server.quit()
        print("✅ 邮件发送成功！")
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        traceback.print_exc()
        raise

# ========== 主流程 ==========
def main():
    print("🚀 GitHub Daily Digest 开始运行...")
    
    # 1. 抓取项目
    projects = fetch_github_trending()
    if not projects:
        print("⚠️ 未获取到任何项目，跳过分析。")
        return

    # 2. 分析
    analysis = analyze_with_qwen(projects)

    # 3. 构建美化后的邮件内容
    subject = "🚀 GitHub 每日热门项目速览 | 自动分析报告"

    # 将 Qwen 的分析按行分割，便于后续对齐（可选）
    analysis_lines = analysis.strip().split('\n')
    
    body = f"""您好！

以下是 {time.strftime('%Y年%m月%d日')} GitHub 全站最热门的开源项目，已由 **Qwen-Max 大模型** 自动生成中文解读：

{'='*60}

{analysis}

{'='*60}
""" 
    # 4. 发送
    send_email(subject, body)
    print("🎉 全部任务完成！")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"💥 程序异常退出: {e}")
        traceback.print_exc()
        sys.exit(1)
