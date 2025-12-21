import os
import re
import json
import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil import tz

# =========================
# 기본 설정
# =========================
KST = tz.gettz("Asia/Seoul")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(ROOT, "posts")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL") or "gpt-4.1-mini"

# =========================
# 수집 소스 (출처별 카테고리)
# =========================
SOURCES = [
    {
        "id": "owid",
        "name": "Our World in Data",
        "kind": "rss",
        "url": "https://ourworldindata.org/atom.xml",
        "limit": 6,
    },
    {
        "id": "worldbank",
        "name": "World Bank",
        "kind": "worldbank_json",
        # World Bank News API (검색 API v2, JSON)   [oai_citation:8‡세계은행](https://www.worldbank.org/ext/en/news?utm_source=chatgpt.com)
        "url": "https://search.worldbank.org/api/v2/news?format=json&rows=12&lang_exact=English",
        "limit": 8,
    },
    {
        "id": "brookings_fp",
        "name": "Brookings (Foreign Policy)",
        "kind": "rss",
        "url": "http://webfeeds.brookings.edu/brookingsrss/topics/usforeignpolicy?format=xml",
        "limit": 6,
    },
    {
        "id": "un_ga",
        "name": "United Nations (GA)",
        "kind": "rss",
        # UN General Assembly RSS 안내 페이지  [oai_citation:9‡유엔](https://www.un.org/en/ga/rss/index.shtml?utm_source=chatgpt.com)
        # (피드 URL은 페이지에서 제공되는 항목을 쓰는 게 가장 안정적이야)
        # 아래는 GA Newsroom RSS 중 하나 예시(환경에 따라 변경될 수 있음).
        "url": "https://www.un.org/en/ga/news/rss.xml",
        "limit": 6,
    },
    {
        "id": "nasa",
        "name": "NASA",
        "kind": "rss",
        # NASA RSS 목록 페이지  [oai_citation:10‡NASA](https://www.nasa.gov/rss-feeds/?utm_source=chatgpt.com)
        "url": "https://www.nasa.gov/rss/dyn/breaking_news.rss",
        "limit": 6,
    },
    {
        "id": "mit_news",
        "name": "MIT News",
        "kind": "rss",
        # MIT News RSS 안내  [oai_citation:11‡MIT News](https://news.mit.edu/rss?utm_source=chatgpt.com)
        "url": "https://news.mit.edu/rss/research",
        "limit": 6,
    },
    {
        "id": "globalvoices",
        "name": "Global Voices",
        "kind": "rss",
        # Global Voices RSS feeds 안내  [oai_citation:12‡Global Voices](https://globalvoices.org/feeds/?utm_source=chatgpt.com)
        "url": "https://globalvoices.org/feed/",
        "limit": 6,
    },
]

# =========================
# 유틸
# =========================
def ensure_dir():
    os.makedirs(POSTS_DIR, exist_ok=True)

def now_kst_iso():
    return datetime.now(tz=KST).isoformat()

def clean_text(html: str) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def as_text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, (int, float, bool)):
        return str(v)
    if isinstance(v, dict):
        for k in ("#text", "text", "value", "name", "title"):
            if k in v:
                return as_text(v[k])
        return " ".join(as_text(x) for x in v.values()).strip()
    if isinstance(v, list):
        return " ".join(as_text(x) for x in v).strip()
    return str(v)

def fallback_summary(text: str, max_len=450) -> str:
    t = re.sub(r"\s+", " ", (text or "")).strip()
    if len(t) <= max_len:
        return t
    cut = t[:max_len]
    last = max(cut.rfind("."), cut.rfind("!"), cut.rfind("?"))
    return (cut[: last + 1] if last > 140 else cut + "…").strip()

# =========================
# OpenAI 한국어 요약
# =========================
def openai_summary(title: str, content: str) -> str | None:
    if not OPENAI_API_KEY:
        return None

    url = "https://api.openai.com/v1/responses"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": OPENAI_MODEL,
        "input": [
            {
                "role": "system",
                "content": (
                    "너는 여러 해외 출처의 글을 매일 읽기 좋게 정리하는 한국어 에디터다. "
                    "반드시 한국어로 자연스럽게 3~5문장 요약을 쓴다. "
                    "원문 문장을 길게 그대로 베끼지 말고 의미를 재구성한다. "
                    "과장/추측 금지. 불확실하면 '명확하지 않음'이라고 적는다."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"[제목]\n{title}\n\n"
                    f"[본문]\n{content}\n\n"
                    "위 글을 한국어로 3~5문장으로 요약해줘. "
                    "무엇이 핵심인지(사실), 왜 중요한지(맥락), 어떤 영향이 있는지(시사점) 중심으로."
                ),
            },
        ],
        "temperature": 0.3,
    }

    r = requests.post(url, headers=headers, json=payload, timeout=45)
    if r.status_code != 200:
        print("OpenAI call failed:", r.status_code)
        print("OpenAI error(head):", r.text[:300])
        return None

    data = r.json()

    out = as_text(data.get("output_text")).strip()
    if out:
        return out

    # Responses 기본 구조(output 배열)에서 텍스트 추출
    texts = []
    for block in data.get("output", []):
        for c in block.get("content", []):
            if isinstance(c, dict):
                if c.get("type") == "output_text" and c.get("text"):
                    texts.append(c["text"])
                elif c.get("text"):
                    texts.append(c["text"])

    out2 = "\n".join(t.strip() for t in texts if t and t.strip()).strip()
    return out2 or None

def summarize(title: str, raw: str) -> str:
    s = openai_summary(title, raw[:6000])
    return s if s else fallback_summary(raw)

# =========================
# 수집 함수
# =========================
def fetch_rss(source_id: str, source_name: str, url: str, limit: int):
    feed = feedparser.parse(url)
    items = []
    for e in feed.entries[:limit]:
        title = (e.get("title") or "").strip()
        link = (e.get("link") or "").strip()

        html = e.get("summary", "")
        if not html and e.get("content"):
            html = (e.get("content")[0].get("value") or "")

        raw = clean_text(html) or title
        published = e.get("published", "") or e.get("updated", "")

        items.append({
            "category": source_id,          # 출처=카테고리
            "source_id": source_id,
            "source": source_name,
            "title": title,
            "url": link,
            "published_at": published,
            "raw_text": raw,
        })
    return items

def fetch_worldbank_news(source_id: str, source_name: str, api_url: str, limit: int):
    r = requests.get(api_url, timeout=45)
    r.raise_for_status()
    data = r.json()

    docs = data.get("documents", {})
    items = []

    # documents는 dict인 경우가 많음
    if isinstance(docs, dict):
        for _, doc in list(docs.items())[:limit]:
            title = as_text(doc.get("title")).strip()
            url = as_text(doc.get("url") or doc.get("link")).strip()
            published = as_text(doc.get("pub_date") or doc.get("date")).strip()

            body_raw = doc.get("body") or doc.get("summary") or doc.get("description") or ""
            raw = clean_text(as_text(body_raw)) or title

            items.append({
                "category": source_id,
                "source_id": source_id,
                "source": source_name,
                "title": title,
                "url": url,
                "published_at": published,
                "raw_text": raw,
            })
    elif isinstance(docs, list):
        for doc in docs[:limit]:
            title = as_text(doc.get("title")).strip()
            url = as_text(doc.get("url") or doc.get("link")).strip()
            published = as_text(doc.get("pub_date") or doc.get("date")).strip()
            body_raw = doc.get("body") or doc.get("summary") or doc.get("description") or ""
            raw = clean_text(as_text(body_raw)) or title

            items.append({
                "category": source_id,
                "source_id": source_id,
                "source": source_name,
                "title": title,
                "url": url,
                "published_at": published,
                "raw_text": raw,
            })

    return items

# =========================
# 메인
# =========================
def main():
    ensure_dir()

    print("DEBUG OPENAI_API_KEY set?:", bool(OPENAI_API_KEY))
    print("DEBUG OPENAI_MODEL:", repr(OPENAI_MODEL))

    collected = []
    for s in SOURCES:
        try:
            if s["kind"] == "rss":
                collected += fetch_rss(s["id"], s["name"], s["url"], s["limit"])
            elif s["kind"] == "worldbank_json":
                collected += fetch_worldbank_news(s["id"], s["name"], s["url"], s["limit"])
        except Exception as e:
            print("Fetch failed:", s["id"], e)

    # 중복 제거
    seen = set()
    items = []
    for it in collected:
        key = (it["title"], it["url"])
        if key in seen:
            continue
        seen.add(key)

        items.append({
            "category": it["category"],  # 출처 카테고리
            "source_id": it["source_id"],
            "source": it["source"],
            "title": it["title"],
            "url": it["url"],
            "published_at": it["published_at"],
            "summary": summarize(it["title"], it["raw_text"]),
        })

    data = {
        "generated_at": now_kst_iso(),
        "sources": [{"id": s["id"], "name": s["name"]} for s in SOURCES],
        "items": items[:40],
    }

    today = datetime.now(tz=KST).strftime("%Y-%m-%d")
    with open(os.path.join(POSTS_DIR, "latest.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    with open(os.path.join(POSTS_DIR, f"{today}.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Generated {len(data['items'])} items")

if __name__ == "__main__":
    main()
