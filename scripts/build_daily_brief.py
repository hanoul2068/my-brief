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
# 모델명은 가장 효율적인 gpt-4o-mini를 추천합니다.
OPENAI_MODEL = os.getenv("OPENAI_MODEL") or "gpt-4o-mini"

SOURCES = [
    {"id": "sbs_headline", "name": "SBS (이 시각 이슈)", "url": "https://news.sbs.co.kr/news/headlineRssFeed.do?plink=RSSREADER", "limit": 5},
    {"id": "sbs_politics", "name": "SBS (정치)", "url": "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=01&plink=RSSREADER", "limit": 5},
    {"id": "yonhap_tv_latest", "name": "연합뉴스TV (최신)", "url": "http://www.yonhapnewstv.co.kr/browse/feed/", "limit": 5},
    {"id": "mk_economy", "name": "매일경제 (경제)", "url": "https://www.mk.co.kr/rss/30100041/", "limit": 5},
    {"id": "hankyung_economy", "name": "한국경제 (경제)", "url": "https://www.hankyung.com/feed/economy", "limit": 5},
    {"id": "koreakr_policy", "name": "정책브리핑 (정책뉴스)", "url": "https://www.korea.kr/rss/policy.xml", "limit": 8},
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
    """기사 원문 페이지에서 본문 텍스트를 추출 (크롤링 강화)"""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # 불필요한 태그 제거
        for s in soup(['script', 'style', 'header', 'footer', 'nav', 'aside', 'form']):
            s.decompose()
            
        # 일반적인 뉴스 본문 영역 태그 찾기
        content = soup.find('article') or soup.find('div', id='articleBody') or soup.find('div', class_='article_view') or soup.find('div', id='news_body_area')
        
        if content:
            return clean_text(content.get_text())
        return ""
    except:
        return ""

def openai_summary(title: str, content: str) -> str | None:
    """OpenAI API를 이용한 5문장 요약 (표준 API 방식)"""
    if not OPENAI_API_KEY:
        return None

    input_text = content if len(content) > 150 else title
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": "너는 한국 뉴스 전문 에디터다. 내용을 [핵심 사실], [배경], [영향 및 전망]이 포함되도록 자연스러운 한국어 5문장으로 요약하라."},
            {"role": "user", "content": f"제목: {title}\n\n본문: {input_text[:3500]}"}
        ],
        "temperature": 0.5,
    }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=40)
        r.raise_for_status()
        return r.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"API Error: {e}")
        return None

def generate_markdown(items):
    """가독성 높은 README 마크다운 생성"""
    now = datetime.now(tz=KST).strftime("%Y-%m-%d %H:%M:%S")
    md = f"# 📰 매일 뉴스 요약 서비스\n\n"
    md += f"> **마지막 업데이트:** {now} (KST)\n\n"
    md += "오늘의 주요 뉴스를 AI가 분석하여 요약해 드립니다. **제목을 클릭**하면 상세 내용을 볼 수 있습니다.\n\n"
    
    icons = {"politics": "⚖️", "economy": "💰", "headline": "🔥", "policy": "📢", "default": "📌"}

    for item in items:
        cat_key = next((k for k in icons if k in item['category']), "default")
        icon = icons[cat_key]
        
        md += f"### {icon} {item['title']}\n"
        md += f"<details>\n<summary>🔍 요약 보기 (출처: {item['source']})</summary>\n\n"
        md += f"**AI 요약:**\n\n{item['summary']}\n\n"
        md += f"[🔗 기사 원문 링크]({item['url']})\n"
        md += f"</details>\n\n---\n"
    
    md += "\n\n---\n*본 콘텐츠는 OpenAI GPT를 통해 자동 요약되었습니다.*"
    return md

# =========================
# 3. 메인 실행부
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
            
            # 유사도 기반 중복 제거 (제목 앞 12자 비교)
            title_key = title[:12].replace(" ", "")
            if title_key in seen_titles: continue
            seen_titles.add(title_key)

            # 본문 추출 및 요약
            full_text = fetch_full_content(link)
            if not full_text:
                full_text = clean_text(e.get("summary", ""))

            summary = openai_summary(title, full_text)
            if not summary:
                summary = (full_text[:200] + "...") if full_text else "요약을 생성할 수 없습니다."

            collected_items.append({
                "category": s["id"],
                "source": s["name"],
                "title": title,
                "url": link,
                "summary": summary
            })
            count += 1
            time.sleep(0.5)

    # 결과 저장 (JSON)
    today = datetime.now(tz=KST).strftime("%Y-%m-%d")
    data = {"generated_at": datetime.now(tz=KST).isoformat(), "items": collected_items}
    
    with open(os.path.join(POSTS_DIR, "latest.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    with open(os.path.join(POSTS_DIR, f"{today}.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # README.md 업데이트
    readme_content = generate_markdown(collected_items)
    with open(os.path.join(ROOT, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme_content)

    print(f"완료: {len(collected_items)}개의 뉴스를 정리했습니다.")

if __name__ == "__main__":
    main()
