import json
import os
import requests
from datetime import datetime

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
    
    # 텔레그램 메시지 시작
    message = f"📅 *{today} 뉴스 브리핑*\n"
    message += "━━━━━━━━━━━━━━\n\n"
    
    for cat in data['categories']:
        if cat['id'] == 'all': continue
        
        # 분야별 10개 뉴스 추출
        cat_items = [it for it in data['items'] if it['category'] == cat['id']][:10]
        if not cat_items: continue
        
        message += f"📂 *{cat['name']} (Top 10)*\n"
        
        for i, item in enumerate(cat_items, 1):
            # 제목에서 불필요한 공백 제거
            title = item['title'].replace('*', '').strip()
            
            # 요약 내용을 3줄 형식으로 다듬기
            # 이미 저장된 summary가 길 경우, 줄바꿈 기준으로 앞 3문장만 추출하거나
            # 불필요한 서술어를 쳐내고 3줄로 재구성 (여기서는 가독성을 위해 포맷팅)
            summary_lines = [line.strip() for line in item['summary'].split('\n') if line.strip()][:3]
            summary_text = "\n".join([f"• {line}" for line in summary_lines])
            
            message += f"*{i}. {title}*\n"
            message += f"{summary_text}\n"
            message += f"[🔗 원문보기]({item['url']})\n\n"
        
        message += "━━━━━━━━━━━━━━\n\n"

    # 텔레그램 API 전송 (메시지가 너무 길면 잘라서 전송)
    send_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    # 메시지 길이 제한(4096자) 대응: 너무 길면 섹션별로 나눠 보내거나 조절이 필요하지만, 
    # 일단 한 번에 보내되 마크다운 모드 적용
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }

    try:
        response = requests.post(send_url, json=payload)
        if response.status_code == 200:
            print("✅ 텔레그램 브리핑 전송 성공!")
        else:
            # 메시지 길이가 초과될 경우를 대비한 간단한 예외 처리
            print(f"❌ 전송 실패: {response.text}")
            if "message is too long" in response.text:
                print("⚠️ 뉴스 양이 너무 많아 메시지 길이가 초과되었습니다. limit을 조정하거나 나눠보내야 합니다.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    send_telegram_msg()
