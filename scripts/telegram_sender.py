import json
import os
import requests
from datetime import datetime

# GitHub Secrets에서 값을 가져옵니다.
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(ROOT, "posts", "latest.json")

def send_telegram_msg():
    if not os.path.exists(DATA_FILE):
        print("데이터 파일이 없습니다.")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    today = datetime.now().strftime("%Y년 %m월 %d일")
    message = f"📢 *{today} 분야별 뉴스 요약*\n\n"
    
    for cat in data['categories']:
        if cat['id'] == 'all': continue
        # 카테고리별 상위 3건 추출
        cat_items = [it for it in data['items'] if it['category'] == cat['id']][:3]
        if not cat_items: continue
        
        message += f"───────────────\n"
        message += f"📂 *{cat['name']}*\n"
        
        for i, item in enumerate(cat_items, 1):
            clean_title = item['title'].replace('*', '').replace('_', '')
            message += f"\n*{i}. {clean_title}*\n"
            # 요약 내용 (텔레그램 글자수 제한 대비)
            summary = item['summary'].replace('\n', ' ')
            message += f"{summary[:200]}...\n"
            message += f"[🔗 원문보기]({item['url']})\n"

    url = f"https://api.openai.com/v1/chat/completions" # 전송용 API
    send_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }

    requests.post(send_url, json=payload)

if __name__ == "__main__":
    send_telegram_msg()
