import json
import os
import requests
from datetime import datetime

# 환경변수 (GitHub Secrets에서 가져옴)
ACCESS_TOKEN = os.getenv("TISTORY_ACCESS_TOKEN")
BLOG_NAME = os.getenv("TISTORY_BLOG_NAME") # 내 블로그 주소 앞부분 (예: mynews)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(ROOT, "posts", "latest.json")

def post_to_tistory():
    if not os.path.exists(DATA_FILE): return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items", [])
    categories = data.get("categories", [])
    
    # 1. 본문 HTML 생성 (티스토리는 HTML 기반)
    today = datetime.now().strftime("%Y년 %m월 %d일")
    title = f"[{today}] 오늘의 분야별 뉴스 심층 분석 요약 (정치, 경제, 사회, 과학)"
    
    content = f"<p>안녕하세요! {today}의 주요 뉴스를 정리해 드립니다.</p><hr/>"

    for cat in categories:
        if cat['id'] == 'all': continue
        cat_items = [it for it in items if it['category'] == cat['id']][:3] # 3건만
        
        if not cat_items: continue
        
        content += f"<h2 style='color: #2c3e50;'>{cat['name']}</h2>"
        for i, it in enumerate(cat_items, 1):
            content += f"<h3 style='background: #f1f3f5; padding: 10px;'>{i}. {it['title']}</h3>"
            content += f"<p style='line-height: 1.8;'>{it['summary'].replace('\n', '<br>')}</p>"
            content += f"<p><a href='{it['url']}' target='_blank'>기사 원문 확인하기</a></p>"
        content += "<hr/>"

    content += "<p>#뉴스요약 #AI요약 #데일리뉴스</p>"

    # 2. 티스토리 API 호출
    url = "https://www.tistory.com/apis/post/write"
    params = {
        "access_token": ACCESS_TOKEN,
        "output": "json",
        "blogName": BLOG_NAME,
        "title": title,
        "content": content,
        "visibility": 3,  # 3: 발행(공개), 0: 비공개
        "category": 0,    # 내 블로그의 카테고리 ID (기본값 0)
    }
    
    response = requests.post(url, data=params)
    if response.status_code == 200:
        print("✅ 티스토리 포스팅 성공!")
    else:
        print(f"❌ 실패: {response.text}")

if __name__ == "__main__":
    post_to_tistory()
