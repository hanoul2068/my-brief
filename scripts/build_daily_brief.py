import os
import re
import json
import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil import tz
import time

# =========================
# 1. 설정 및 환경 변수
# =========================
KST = tz.gettz("Asia/Seoul")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(ROOT, "posts")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL") or "gpt-4o-mini"

# 사회, 과학을 포함한 뉴스 소스 (전체 약 60~70개 수집 -> 중복 제거 후 50~60개 목표)
SOURCES = [
    {"id": "headline", "name": "주요뉴스 (연합TV)", "url": "http://www.yonhapnewstv.co.kr/browse/feed/", "limit": 10},
    {"id": "society", "name": "사회 (YTN)", "url": "https://www.ytn.co.kr/_ln/rss/0103.xml", "limit": 10},
    {"id": "politics", "name": "정치 (SBS)", "url": "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=01&plink=RSSREADER", "limit": 10},
    {"id": "economy", "name": "경제 (한경)", "url": "https://www.hankyung.com/feed/economy", "limit": 10},
    {"id": "science", "name": "IT/과학 (SBS)", "url": "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=08&plink=RSSREADER", "limit": 10},
    {"id": "science", "name": "과학 (매경)", "url": "https://www.mk.co.kr/rss/30100041/", "limit": 10},
    {"id": "policy", "name": "정책브리핑", "url": "https://www.korea.kr/rss/policy.xml", "limit": 12},
]

DISPLAY_CATEGORIES = [
    {"id": "all", "name": "전체"},
    {"id": "headline", "name": "🔥 주요소식"},
    {"id": "politics", "name": "⚖️ 정치"},
    {"id": "economy", "name": "💰 경제/IT"},
    {"id": "society", "name": "👥 사회/생활"},
    {"id": "science", "name": "🧪 과학/기술"},
    {"id": "policy", "name": "📢 정부/정책"}
]

# =========================
# 2. 유틸리티 함수
# =========================
def ensure_dir():
    os.makedirs(POSTS_DIR, exist_ok=True)

def clean_text(text: str) -> str:
    if not text: return ""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def fetch_full_content(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, "html.parser")
        for s in soup(['script', 'style', 'header', 'footer', 'nav', 'aside', 'form', 'iframe']):
            s.decompose()
        content = soup.find('article') or soup.find('div', id='articleBody') or soup.find('div', class_='article_view') or soup.find('div', id='news_body_area')
        return clean_text(content.get_text()) if content else ""
    except:
        return ""

def openai_summary(title: str, content: str) -> str | None:
    if not OPENAI_API_KEY: return None
    input_text = content if len(content) > 150 else title
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {
                "role": "system", 
                "content": (
                    "너는 전문 뉴스 분석가다. 독자가 원문을 보지 않아도 맥락을 완벽히 이해하도록 심층 요약을 제공한다. "
                    "내용은 반드시 다음 3섹션으로 나누어 총 10문장 내외로 작성하라.\n\n"
                    "1. [핵심 사실]: 사건의 핵심 요지를 상세히 기술 (3-4문장)\n"
                    "2. [맥락과 배경]: 이 사건이 왜 발생했는지, 이전 상황은 어떠했는지 설명 (3문장)\n"
                    "3. [전망 및 분석]: 앞으로의 영향과 향후 관전 포인트 제시 (3문장)\n\n"
                    "구체적인 수치나 고유명사를 포함하여 분석적인 톤으로 작성하라."
                )
            },
            {"role": "user", "content": f"제목: {title}\n\n본문: {input_text[:3500]}"}
        ],
        "temperature": 0.5,
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=45)
        return r.json()['choices'][0]['message']['content'].strip()
    except:
        return None

# =========================
# 3. 실행 프로세스
# =========================
def main():
    ensure_dir()
    collected_items = []
    seen_titles = set()

    for s in SOURCES:
        print(f"📡 수집 중: {s['name']}...")
        feed = feedparser.parse(s["url"])
        count = 0
        for e in feed.entries:
            if count >= s["limit"]: break
            title = e.get("title", "").strip()
            link = e.get("link", "").strip()
            
            title_key = title[:12].replace(" ", "")
            if title_key in seen_titles: continue
            seen_titles.add(title_key)

            full_text = fetch_full_content(link) or clean_text(e.get("summary", ""))
            summary = openai_summary(title, full_text)
            
            collected_items.append({
                "category": s["id"],
                "source": s["name"],
                "title": title,
                "url": link,
                "published_at": datetime.now(tz=KST).strftime("%Y-%m-%d %H:%M"),
                "summary": summary or "요약을 불러오지 못했습니다."
            })
            count += 1
            time.sleep(0.5)

    final_data = {
        "generated_at": datetime.now(tz=KST).isoformat(),
        "categories": DISPLAY_CATEGORIES,
        "items": collected_items[:65]
    }

    today = datetime.now(tz=KST).strftime("%Y-%m-%d")
    for filename in ["latest.json", f"{today}.json"]:
        with open(os.path.join(POSTS_DIR, filename), "w", encoding="utf-8") as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)

    print(f"✅ 저장 완료: 총 {len(final_data['items'])}건")

if __name__ == "__main__":
    main()
