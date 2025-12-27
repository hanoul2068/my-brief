import json
import os
import requests
from datetime import datetime
import time

# 설정
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
    
    # 1. 시작 알림 메시지 전송
    start_msg = f"📅 *{today} 뉴스 브리핑을 시작합니다*\n━━━━━━━━━━━━━━"
    send_to_telegram(start_msg)
    time.sleep(1) # 전송 간격 조절

    # 2. 카테고리별로 루프를 돌며 개별 메시지 전송
    for cat in data['categories']:
        if cat['id'] == 'all': continue
        
        # 분야별 10개 뉴스 추출
        cat_items = [it for it in data['items'] if it['category'] == cat['id']][:10]
        if not cat_items: continue
        
        # 카테고리 헤더
        message = f"📂 *{cat['name']} (Top 10)*\n"
        message += "━━━━━━━━━━━━━━\n\n"
        
        for i, item in enumerate(cat_items, 1):
            title = item['title'].replace('*', '').strip()
            
            # 요약 내용 처리 (줄바꿈 및 가독성)
            summary_lines = [line.strip() for line in item['summary'].split('\n') if line.strip()][:3]
            summary_text = "\n".join([f"• {line}" for line in summary_lines])
            
            item_msg = f"*{i}. {title}*\n{summary_text}\n[🔗 원문보기]({item['url']})\n\n"
            
            # 메시지 길이가 너무 길어지면 일단 전송하고 새로 시작 (안전장치)
            if len(message + item_msg) > 3800:
                send_to_telegram(message)
                message = f"📂 *{cat['name']} (계속)*\n━━━━━━━━━━━━━━\n\n"
            
            message += item_msg
        
        # 카테고리별 전송
        send_to_telegram(message)
        time.sleep(1.5) # 텔레그램 API 도배 방지를 위한 휴식

def send_to_telegram(text):
    """실제 텔레그램 API 호출 함수"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        res = requests.post(url, json=payload)
        if res.status_code != 200:
            print(f"❌ 전송 실패: {res.text}")
    except Exception as e:
        print(f"❌ 오류: {e}")

if __name__ == "__main__":
    send_telegram_msg()
