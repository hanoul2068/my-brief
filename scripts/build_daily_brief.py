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
# 1. 기본 설정
# =========================
KST = tz.gettz("Asia/Seoul")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(ROOT, "posts")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL") or "gpt-4o-mini"

# 장르별 뉴스 소스 설정
SOURCES = [
    {"id": "politics", "name": "정치 (SBS)", "url": "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=01&plink=RSSREADER", "limit": 5},
    {"id": "politics", "name": "정치 (매경)", "url": "https://www.mk.co.kr/rss/30200030/", "limit": 5},
    {"id": "economy", "name": "경제 (SBS)", "url": "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=02&plink=RSSREADER", "limit": 5},
    {"id": "economy", "name": "경제 (한경)", "url": "https://www.hankyung.com/feed/economy", "limit": 5},
    {"id": "headline", "name": "주요뉴스 (연합TV)", "url": "http://www.yonhapnewstv.co.kr/browse/feed/", "limit": 5},
    {"id": "policy", "name": "정책브리핑", "url": "https://www.korea.kr/rss/policy.xml", "limit": 10},
]

# HTML 상단에 표시될 카테고리 버튼 정의
DISPLAY_CATEGORIES = [
    {"id": "all", "name": "전체"},
    {"id": "headline", "name": "🔥 주요소식"},
    {"id": "politics", "name": "⚖️ 정치"},
    {"id": "economy", "name": "💰 경제/IT"},
    {"id": "policy", "name": "📢 정부/정책"}
]

# =========================
# 2. 유틸리티 및 크롤링
# =========================
def ensure_dir():
    os.makedirs(POSTS_DIR, exist_ok=True)

def clean_text(text: str) -> str:
    if not text: return ""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def fetch_full_content(url: str) -> str:
    """기사 원문 본문 추출"""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, "html.parser")
        for s in soup(['script', 'style', 'header', 'footer', 'nav', 'aside', 'form']):
            s.decompose()
        content = soup.find('article') or soup.find('div', id='articleBody') or soup.find('div', class_='article_view') or soup.find('div', id='news_body_area')
        return clean_text(content.get_text()) if content else ""
    except:
        return ""

def openai_summary(title: str, content: str) -> str | None:
    """OpenAI API 요약"""
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
                    "너는 전문적인 뉴스 분석가이자 에디터다. "
                    "독자가 원문을 보지 않아도 맥락을 완벽히 이해할 수 있도록 '심층 분석 요약'을 제공한다. "
                    "내용은 반드시 다음 3가지 섹션으로 나누어 총 10문장 내외로 작성하라.\n\n"
                    "1. [사건의 핵심]: 누가, 언제, 무엇을 했는지 상세히 기술 (3-4문장)\n"
                    "2. [맥락과 배경]: 이 사건이 왜 발생했는지, 이전 상황은 어떠했는지 설명 (3문장)\n"
                    "3. [쟁점 및 전망]: 앞으로의 영향, 이해관계자들의 입장, 향후 관전 포인트 제시 (3문장)\n\n"
                    "격식 있고 분석적인 톤을 유지하며, 구체적인 수치나 고유명사가 본문에 있다면 반드시 포함하라."
                )
            },
            {
                "role": "user", 
                "content": f"제목: {title}\n\n본문: {input_text[:3500]}"
            }
        ],
        "temperature": 0.5,
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=40)
        return r.json()['choices'][0]['message']['content'].strip()
    except:
        return None

def generate_markdown(items):
    """README용 마크다운 생성"""
    now = datetime.now(tz=KST).strftime("%Y-%m-%d %H:%M:%S")
    md = f"# 📰 World Brief 뉴스 요약\n\n> 업데이트: {now}\n\n"
    for item in items[:15]: # 상위 15개만 요약 노출
        md += f"### {item['title']}\n<details><summary>요약 보기 ({item['source']})</summary>\n\n{item['summary']}\n\n[원문 읽기]({item['url']})\n</details>\n\n"
    return md

# =========================
# 3. 메인 실행
# =========================
def main():
    ensure_dir()
    collected_items = []
    seen_titles = set()

    for s in SOURCES:
        print(f"수집 중: {s['name']}...")
        feed = feedparser.parse(s["url"])
        
        count = 0
        for e in feed.entries:
            if count >= s["limit"]: break
            title = e.get("title", "").strip()
            link = e.get("link", "").strip()
            
            # 중복 체크
            title_key = title[:12].replace(" ", "")
            if title_key in seen_titles: continue
            seen_titles.add(title_key)

            full_text = fetch_full_content(link) or clean_text(e.get("summary", ""))
            summary = openai_summary(title, full_text) or (full_text[:200] + "...")

            collected_items.append({
                "category": s["id"], # politics, economy 등
                "source": s["name"],
                "title": title,
                "url": link,
                "published_at": datetime.now(tz=KST).strftime("%Y-%m-%d %H:%M"),
                "summary": summary
            })
            count += 1
            time.sleep(0.3)

    # 데이터 구성
    final_data = {
        "generated_at": datetime.now(tz=KST).isoformat(),
        "categories": DISPLAY_CATEGORIES,
        "items": collected_items
    }

    # 파일 저장
    today = datetime.now(tz=KST).strftime("%Y-%m-%d")
    for f_path in ["latest.json", f"{today}.json"]:
        with open(os.path.join(POSTS_DIR, f_path), "w", encoding="utf-8") as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)

    # README 업데이트
    with open(os.path.join(ROOT, "README.md"), "w", encoding="utf-8") as f:
        f.write(generate_markdown(collected_items))

    print(f"완료: {len(collected_items)}개 항목 저장.")

if __name__ == "__main__":
    main()
