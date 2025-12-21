import os, re, json, time
from datetime import datetime, timezone
from dateutil import tz
import requests
import feedparser
from bs4 import BeautifulSoup

KST = tz.gettz("Asia/Seoul")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(ROOT, "posts")

def now_kst_iso():
    return datetime.now(tz=KST).isoformat()

def ensure_dirs():
    os.makedirs(POSTS_DIR, exist_ok=True)

def clean_text(html: str) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    return text
    
def as_text(v) -> str:
    """문자열/딕트/리스트가 섞여 내려오는 값을 안전하게 문자열로 변환"""
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, (int, float, bool)):
        return str(v)
    if isinstance(v, dict):
        # 흔한 케이스: {"#text": "..."} 또는 {"text": "..."} 또는 {"value": "..."}
        for k in ("#text", "text", "value", "name", "title"):
            if k in v and isinstance(v[k], (str, int, float, bool)):
                return str(v[k])
        return " ".join([as_text(x) for x in v.values()]).strip()
    if isinstance(v, list):
        return " ".join(as_text(x) for x in v).strip()
    return str(v)

def simple_extract_summary(text: str, max_chars=550) -> str:
    # 아주 단순 추출 요약: 앞부분을 문장 단위로 자름
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    # 마지막 문장 경계 찾기
    m = re.finditer(r"[.!?]\s", cut)
    last = None
    for x in m:
        last = x.end()
    if last and last > 180:
        return cut[:last].strip()
    return cut.strip() + "…"

def openai_summarize(title: str, content: str) -> str | None:
    """
    선택: OpenAI API로 요약
    - GitHub Secrets에 OPENAI_API_KEY 설정 필요
    - 원문 복제를 피하려고 content는 '본문 전체'가 아니라 '추출 텍스트'로 넣되,
      결과는 반드시 '요약'만 저장
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    # OpenAI API 호출(HTTP). 모델명은 사용 환경에 맞게 바꿔도 됨.
    # 여기선 범용적으로 'gpt-4.1-mini' 같은 이름을 예시로 둠.
    url = "https://api.openai.com/v1/responses"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        "input": [
            {
                "role": "system",
                "content": (
                    "너는 '세계경제/국제정치' 브리핑을 쓰는 한국어 에디터다. "
                    "반드시 한국어로 자연스럽게 요약한다. "
                    "원문 문장을 그대로 길게 베끼지 말고, 의미를 재구성해라. "
                    "과장/추측 금지. 불확실하면 '추정' 또는 '명확하지 않음'이라고 써라. "
                    "형식: 3~5문장 단락 1개. "
                    "가능하면 (무엇/왜 중요/영향) 순서로 정리."
                )
            },
            {
                "role": "user",
                "content": (
                    f"아래 글을 한국어로 3~5문장으로 요약해줘.\n"
                    f"- 숫자/고유명사가 핵심이면 유지\n"
                    f"- 원문 표현을 길게 복사하지 말 것\n\n"
                    f"[제목]\n{title}\n\n"
                    f"[본문(추출 텍스트)]\n{content}\n"
                )
            }
        ],
        "temperature": 0.3
    }
    r = requests.post(url, headers=headers, json=payload, timeout=45)
    if r.status_code != 200:
        return None
    data = r.json()
    # Responses API는 output_text가 있을 수 있음
    summary = data.get("output_text")
    if not summary:
        # fallback: 구조가 다르면 최소한의 파싱
        try:
            summary = data["output"][0]["content"][0]["text"]
        except Exception:
            return None
    return summary.strip()

def summarize(title: str, content: str) -> str:
    content = content.strip()
    s = openai_summarize(title, content)
    if s:
        return s
    return simple_extract_summary(content)

def fetch_atom(feed_url: str, source: str, category: str, limit: int = 8):
    d = feedparser.parse(feed_url)
    items = []
    for e in d.entries[:limit]:
        title = e.get("title", "").strip()
        url = e.get("link", "").strip()
        published = e.get("published", "") or e.get("updated", "")
        # OWID atom은 summary/content에 html이 들어올 수 있음
        html = e.get("summary", "") or (e.get("content", [{}])[0].get("value", "") if e.get("content") else "")
        text = clean_text(html)
        if not text:
            text = title
        items.append({
            "category": category,
            "source": source,
            "title": title,
            "url": url,
            "published_at": published,
            "raw_text": text
        })
    return items

def fetch_worldbank_json(api_url: str, source: str, category: str, limit: int = 8):
    r = requests.get(api_url, timeout=45)
    r.raise_for_status()
    data = r.json()

    docs = data.get("documents", {})
    items = []

    # documents가 dict일 수도, list일 수도 있어서 둘 다 처리
    if isinstance(docs, dict):
        iterable = list(docs.items())
        for _, doc in iterable[:limit]:
            title = as_text(doc.get("title")).strip()
            url = as_text(doc.get("url") or doc.get("link")).strip()
            published = as_text(doc.get("pub_date") or doc.get("date")).strip()

            body_raw = doc.get("body") or doc.get("summary") or doc.get("description") or ""
            body = clean_text(as_text(body_raw))
            if not body:
                body = title or url

            items.append({
                "category": category,
                "source": source,
                "title": title,
                "url": url,
                "published_at": published,
                "raw_text": body
            })

    elif isinstance(docs, list):
        for doc in docs[:limit]:
            title = as_text(doc.get("title")).strip()
            url = as_text(doc.get("url") or doc.get("link")).strip()
            published = as_text(doc.get("pub_date") or doc.get("date")).strip()

            body_raw = doc.get("body") or doc.get("summary") or doc.get("description") or ""
            body = clean_text(as_text(body_raw))
            if not body:
                body = title or url

            items.append({
                "category": category,
                "source": source,
                "title": title,
                "url": url,
                "published_at": published,
                "raw_text": body
            })

    return items

def keyword_filter(items, include_keywords):
    out = []
    for it in items:
        hay = (it["title"] + " " + it.get("raw_text","")).lower()
        if any(k in hay for k in include_keywords):
            out.append(it)
    return out

def main():
    ensure_dirs()

    # === 수집 소스 ===
    # OWID: 사이트 내에 RSS(Atom) 안내가 있음 
    OWID_RESEARCH_ATOM = "https://ourworldindata.org/atom.xml"
    OWID_INSIGHTS_ATOM = "https://ourworldindata.org/atom-data-insights.xml"

    # World Bank: 공식 뉴스 페이지에 JSON API 엔드포인트가 노출됨 
    WB_PRESS = "https://search.worldbank.org/api/v2/news?format=json&rows=20&lang_exact=English&displayconttype_exact=Press%20Release&os=0"
    WB_STATEMENT = "https://search.worldbank.org/api/v2/news?format=json&rows=20&lang_exact=English&displayconttype_exact=Statement&os=0"

    # Brookings: (실무에서 널리 쓰이는 webfeeds) — 정치/외교 주제
    BROOKINGS_US_FOREIGN_POLICY = "http://webfeeds.brookings.edu/brookingsrss/topics/usforeignpolicy?format=xml"
    BROOKINGS_GLOBAL_ECON_DEV   = "http://webfeeds.brookings.edu/brookingsrss/programs/globaleconomyanddevelopment?format=xml"

    items = []

    # === 경제: OWID + World Bank + (보조) Brookings 글로벌경제 ===
    owid_r = fetch_atom(OWID_RESEARCH_ATOM, "Our World in Data", "economy", limit=10)
    owid_i = fetch_atom(OWID_INSIGHTS_ATOM, "Our World in Data", "economy", limit=10)

    # OWID에서 경제 관련 키워드로 대충 필터(원하면 더 촘촘히 가능)
    econ_kw = ["gdp","inflation","trade","globalization","debt","interest rate","economy","recession","growth","unemployment","poverty"]
    owid_all = keyword_filter(owid_r + owid_i, econ_kw)[:10]

    wb_pr = fetch_worldbank_json(WB_PRESS, "World Bank", "economy", limit=8)
    wb_st = fetch_worldbank_json(WB_STATEMENT, "World Bank", "economy", limit=6)

    br_econ = fetch_atom(BROOKINGS_GLOBAL_ECON_DEV, "Brookings", "economy", limit=6)

    # === 정치: Brookings 외교 ===
    br_pol = fetch_atom(BROOKINGS_US_FOREIGN_POLICY, "Brookings", "politics", limit=10)

    items.extend(owid_all)
    items.extend(wb_pr)
    items.extend(wb_st)
    items.extend(br_econ)
    items.extend(br_pol)

    # === 요약 생성(원문 복제 X) ===
    final = []
    seen = set()
    for it in items:
        key = (it["title"], it["url"])
        if key in seen:
            continue
        seen.add(key)
        content = it.get("raw_text","")[:6000]  # 과도한 입력 방지
        summary = summarize(it["title"], content)
        final.append({
            "category": it["category"],
            "source": it["source"],
            "title": it["title"],
            "url": it["url"],
            "published_at": it.get("published_at",""),
            "summary": summary
        })

    # 최신순 흉내(날짜 파싱이 불완전할 수 있어 title/순서 기반도 섞임)
    # 여기선 수집 순서 기준으로 두고, 화면에서 필터링만 제공
    out = {
        "generated_at": now_kst_iso(),
        "items": final[:20]  # 하루 20개로 제한
    }

    today = datetime.now(tz=KST).strftime("%Y-%m-%d")
    daily_path = os.path.join(POSTS_DIR, f"{today}.json")
    latest_path = os.path.join(POSTS_DIR, "latest.json")

    with open(daily_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Generated: {daily_path} and latest.json with {len(out['items'])} items")

if __name__ == "__main__":
    main()
