import os
import re
import json
import requests
import feedparser
from datetime import datetime
from bs4 import BeautifulSoup
from dateutil import tz

# =========================
# 기본 설정
# =========================
KST = tz.gettz("Asia/Seoul")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(ROOT, "posts")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


# =========================
# 유틸 함수
# =========================
def now_kst():
    return datetime.now(tz=KST).isoformat()


def ensure_dir():
    os.makedirs(POSTS_DIR, exist_ok=True)


def clean_text(html: str) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


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
        return " ".join(as_text(x) for x in v.values())
    if isinstance(v, list):
        return " ".join(as_text(x) for x in v)
    return str(v)


def fallback_summary(text: str, max_len=450):
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_len:
        return text
    cut = text[:max_len]
    last = max(cut.rfind("."), cut.rfind("!"), cut.rfind("?"))
    return cut[: last + 1] if last > 150 else cut + "…"


# =========================
# OpenAI 한국어 요약
# =========================
def openai_summary(title: str, content: str) -> str | None:
    if not OPENAI_API_KEY:
        print("OPENAI_API_KEY is missing -> fallback summary")
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
                    "너는 세계경제·국제정치를 정리하는 한국어 뉴스 에디터다. "
                    "반드시 한국어로 자연스럽게 요약한다. "
                    "원문 문장을 길게 베끼지 말고 의미를 재구성해라. "
                    "과장·추측 금지. 불확실하면 그렇게 명시. "
                    "형식은 3~5문장 단락 1개."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"[제목]\n{title}\n\n"
                    f"[본문]\n{content}\n\n"
                    "위 글을 한국어로 3~5문장으로 요약해줘. "
                    "무엇/왜 중요/영향 중심으로."
                ),
            },
        ],
        "temperature": 0.3,
    }

    r = requests.post(url, headers=headers, json=payload, timeout=45)

    # 실패 로그를 남겨서 원인 추적 가능하게
    if r.status_code != 200:
        print("OpenAI call failed:", r.status_code)
        print("OpenAI error (head):", r.text[:300])
        return None

    data = r.json()

    # 1) 있으면 바로 사용
    out = (data.get("output_text") or "").strip()
    if out:
        return out

    # 2) Responses 표준 구조(output 배열)에서 텍스트 추출
    try:
        texts = []
        for block in data.get("output", []):
            for c in block.get("content", []):
                # text 타입
                if isinstance(c, dict) and c.get("type") == "output_text" and c.get("text"):
                    texts.append(c["text"])
                # 혹시 다른 형태로 들어오는 경우 대비
                if isinstance(c, dict) and c.get("text"):
                    texts.append(c["text"])
        out2 = "\n".join(t.strip() for t in texts if t and t.strip()).strip()
        if out2:
            return out2
    except Exception as e:
        print("OpenAI parse error:", e)

    # 여기까지 왔으면 파싱 실패 -> fallback
    print("OpenAI returned no parsable text -> fallback")
    return None


def summarize(title: str, content: str) -> str:
    s = openai_summary(title, content)
    return s if s else fallback_summary(content)


# =========================
# 데이터 수집
# =========================
def fetch_atom(url, source, category, limit=8):
    feed = feedparser.parse(url)
    items = []
    for e in feed.entries[:limit]:
        title = e.get("title", "")
        link = e.get("link", "")
        html = e.get("summary", "") or e.get("content", [{}])[0].get("value", "")
        text = clean_text(html) or title
        items.append(
            {
                "category": category,
                "source": source,
                "title": title.strip(),
                "url": link.strip(),
                "published_at": e.get("published", ""),
                "raw": text,
            }
        )
    return items


def fetch_worldbank(api_url, limit=8):
    r = requests.get(api_url, timeout=45)
    r.raise_for_status()
    data = r.json()
    docs = data.get("documents", {})
    items = []

    for _, d in list(docs.items())[:limit]:
        title = as_text(d.get("title"))
        url = as_text(d.get("url") or d.get("link"))
        body = clean_text(as_text(d.get("body") or d.get("summary")))
        items.append(
            {
                "category": "economy",
                "source": "World Bank",
                "title": title,
                "url": url,
                "published_at": as_text(d.get("pub_date")),
                "raw": body or title,
            }
        )
    return items


# =========================
# 메인 실행
# =========================
def main():
    ensure_dir()

    items = []

    # 세계 경제
    items += fetch_atom(
        "https://ourworldindata.org/atom.xml",
        "Our World in Data",
        "economy",
        6,
    )

    items += fetch_worldbank(
        "https://search.worldbank.org/api/v2/news?format=json&rows=10"
    )

    # 세계 정치
    items += fetch_atom(
        "http://webfeeds.brookings.edu/brookingsrss/topics/usforeignpolicy?format=xml",
        "Brookings",
        "politics",
        6,
    )

    final = []
    seen = set()

    for it in items:
        key = (it["title"], it["url"])
        if key in seen:
            continue
        seen.add(key)

        summary = summarize(it["title"], it["raw"][:6000])
        final.append(
            {
                "category": it["category"],
                "source": it["source"],
                "title": it["title"],
                "url": it["url"],
                "published_at": it["published_at"],
                "summary": summary,
            }
        )

    data = {
        "generated_at": now_kst(),
        "items": final[:20],
    }

    today = datetime.now(tz=KST).strftime("%Y-%m-%d")
    with open(os.path.join(POSTS_DIR, "latest.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    with open(os.path.join(POSTS_DIR, f"{today}.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Generated {len(data['items'])} items")


if __name__ == "__main__":
    main()
