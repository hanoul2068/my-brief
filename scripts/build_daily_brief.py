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
# 기본 설정
# =========================
KST = tz.gettz("Asia/Seoul")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(ROOT, "posts")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# 모델명이 gpt-4.1-mini는 존재하지 않으므로 표준인 gpt-4o-mini로 기본값 설정
OPENAI_MODEL = os.getenv("OPENAI_MODEL") or "gpt-4o-mini"

SOURCES = [
    {"id": "sbs_headline", "name": "SBS (이 시각 이슈)", "url": "https://news.sbs.co.kr/news/headlineRssFeed.do?plink=RSSREADER", "limit": 5},
    {"id": "sbs_politics", "name": "SBS (정치)", "url": "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=01&plink=RSSREADER", "limit": 5},
    {"id": "sbs_economy", "name": "SBS (경제)", "url": "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=02&plink=RSSREADER", "limit": 5},
    {"id": "yonhap_tv_latest", "name": "연합뉴스TV (최신)", "url": "http://www.yonhapnewstv.co.kr/browse/feed/", "limit": 5},
    {"id": "mk_economy", "name": "매일경제 (경제)", "url": "https://www.mk.co.kr/rss/30100041/", "limit": 5},
    {"id": "hankyung_economy", "name": "한국경제 (경제)", "url": "https://www.hankyung.com/feed/economy", "limit": 5},
    {"id": "koreakr_policy", "name": "정책브리핑 (정책뉴스)", "url": "https://www.korea.kr/rss/policy.xml", "limit": 8},
]

# =========================
# 유틸 및 크롤링 강화
# =========================
def ensure_dir():
    os.makedirs(POSTS_DIR, exist_ok=True)

def clean_text(text: str) -> str:
    if not text: return ""
    # 불필요한 공백 및 특수문자 정제
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def fetch_full_content(url: str) -> str:
    """RSS 요약 대신 실제 기사 페이지에서 본문을 추출 시도"""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # 일반적인 뉴스 사이트의 본문 영역 태그들 제거 (광고, 스크립트 등)
        for s in soup(['script', 'style', 'header', 'footer', 'nav', 'aside']):
            s.decompose()
            
        # 주요 언론사별 본문 태그 탐색 (기본적으로 article이나 특정 id/class 사용)
        content = soup.find('article') or soup.find('div', id='articleBody') or soup.find('div', class_='article_view')
        
        if content:
            return clean_text(content.get_text())
        return ""
    except Exception as e:
        print(f"Full content fetch failed for {url}: {e}")
        return ""

# =========================
# OpenAI API (표준 ChatCompletion)
# =========================
def openai_summary(title: str, content: str) -> str | None:
    if not OPENAI_API_KEY:
        return None

    # 본문이 너무 짧으면 제목만이라도 활용, 너무 길면 자름
    input_text = content if len(content) > 100 else title
    
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {
                "role": "system", 
                "content": "너는 한국 뉴스 전문 에디터다. 내용을 [핵심 사실], [배경], [영향 및 전망]이 포함되도록 자연스러운 한국어 5문장으로 요약하라."
            },
            {
                "role": "user", 
                "content": f"제목: {title}\n\n본문: {input_text[:3000]}" # 토큰 절약을 위해 3000자 제한
            }
        ],
        "temperature": 0.5,
    }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        r.raise_for_status()
        result = r.json()
        return result['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"OpenAI API Error: {e}")
        return None

# =========================
# 메인 로직
# =========================
def main():
    ensure_dir()
    collected_items = []
    seen_titles = set()

    for s in SOURCES:
        print(f"Fetching: {s['name']}")
        feed = feedparser.parse(s["url"])
        
        count = 0
        for e in feed.entries:
            if count >= s["limit"]: break
            
            title = e.get("title", "").strip()
            link = e.get("link", "").strip()
            
            # 1. 중복 제거 (제목 앞 12글자가 같으면 동일 기사로 간주하는 유사도 체크)
            title_key = title[:12].replace(" ", "")
            if title_key in seen_titles: continue
            seen_titles.add(title_key)

            # 2. 본문 크롤링 시도
            full_text = fetch_full_content(link)
            if not full_text:
                full_text = clean_text(e.get("summary", ""))

            # 3. 요약 수행
            summary = openai_summary(title, full_text)
            if not summary:
                # API 실패 시 RSS 기본 요약이나 본문 앞부분 자르기
                summary = (full_text[:200] + "...") if full_text else "요약을 생성할 수 없습니다."

            collected_items.append({
                "category": s["id"],
                "source": s["name"],
                "title": title,
                "url": link,
                "published_at": e.get("published", datetime.now(tz=KST).isoformat()),
                "summary": summary
            })
            count += 1
            time.sleep(0.5) # 서버 부하 방지용 짧은 휴식

    # 결과 저장
    data = {
        "generated_at": datetime.now(tz=KST).isoformat(),
        "items": collected_items
    }

    today = datetime.now(tz=KST).strftime("%Y-%m-%d")
    for filename in ["latest.json", f"{today}.json"]:
        with open(os.path.join(POSTS_DIR, filename), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Success: {len(collected_items)} news items saved.")

if __name__ == "__main__":
    main()
