const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));

let DATA = null;
let FILTER = "all";

function fmt(dt) {
  try { return new Date(dt).toLocaleString("ko-KR"); } catch { return dt; }
}

function render() {
  if (!DATA) return;
  $("#meta").textContent = `업데이트: ${fmt(DATA.generated_at)} · 총 ${DATA.items.length}건`;

  const items = DATA.items.filter(x => FILTER === "all" ? true : x.category === FILTER);
  $("#list").innerHTML = items.map(x => `
    <article class="item">
      <div class="kicker">
        <span class="tag">${x.category === "economy" ? "경제" : "정치"}</span>
        <span class="tag">${x.source}</span>
        <span>${x.published_at ? fmt(x.published_at) : ""}</span>
      </div>
      <h3 class="title">${escapeHtml(x.title)}</h3>
      <p class="summary">${escapeHtml(x.summary)}</p>
      <div class="links">
        <a href="${x.url}" target="_blank" rel="noopener noreferrer">원문 보기</a>
      </div>
    </article>
  `).join("");
}

function escapeHtml(s) {
  return (s ?? "").replace(/[&<>"']/g, (m) => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
  })[m]);
}

async function load() {
  // 가장 최근 파일을 고정 경로로 두기 위해 posts/latest.json 사용
  const r = await fetch("posts/latest.json", { cache: "no-store" });
  DATA = await r.json();
  render();
}

$$(".btn").forEach(b => {
  b.addEventListener("click", () => {
    $$(".btn").forEach(x => x.classList.remove("active"));
    b.classList.add("active");
    FILTER = b.dataset.filter;
    render();
  });
});

load();
