# 使用 github-trending 的简化版逻辑
import requests
from bs4 import BeautifulSoup
import json

def get_daily_trending():
    url = "https://github.com/trending?since=daily"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(resp.text, 'html.parser')
    repos = []
    for item in soup.select('article h2 a'):
        name = item.text.strip().replace('\n', '').replace(' ', '')
        link = "https://github.com" + item['href']
        desc_elem = item.find_next('p')
        desc = desc_elem.text.strip() if desc_elem else ""
        repos.append({"name": name, "link": link, "description": desc})
        if len(repos) >= 10: break
    return repos
