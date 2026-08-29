const DATA_URL = "./data/news.json";

let allNews = [];
let activeFilter = "all";

const categories = [
  ["all", "すべて"],
  ["ucl", "CL"],
  ["epl", "プレミア"],
  ["laliga", "ラ・リーガ"],
  ["seriea", "セリエA"],
  ["bundesliga", "ブンデス"],
  ["other", "その他"],
  ["transfer", "移籍"]
];

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderFilters() {
  const filters = document.querySelector("#filters");
  if (!filters) return;

  filters.innerHTML = categories.map(([id, label]) => {
    return `
      <button
        class="filter ${id === activeFilter ? "active" : ""}"
        data-filter="${id}"
      >
        ${label}
      </button>
    `;
  }).join("");

  filters.querySelectorAll(".filter").forEach(button => {
    button.addEventListener("click", () => {
      activeFilter = button.dataset.filter;
      renderFilters();
      renderNews();
    });
  });
}

function renderNews() {
  const newsEl = document.querySelector("#news");
  const countEl = document.querySelector("#count");
  const searchEl = document.querySelector("#search");

  if (!newsEl) return;

  const query = (searchEl?.value || "").trim().toLowerCase();

  const filtered = allNews.filter(item => {
    const categoryMatch =
      activeFilter === "all" ||
      item.category === activeFilter ||
      item.type === activeFilter;

    const text = [
      item.title,
      item.summary,
      item.source,
      item.label,
      item.category,
      item.type
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();

    const searchMatch = !query || text.includes(query);

    return categoryMatch && searchMatch;
  });

  if (countEl) {
    countEl.textContent = `${filtered.length}件`;
  }

  if (!filtered.length) {
    newsEl.innerHTML =
      '<div class="empty">該当するニュースがありません。</div>';
    return;
  }

  newsEl.innerHTML = filtered.map(item => {
    const title = escapeHtml(item.title || "タイトルなし");
    const summary = escapeHtml(item.summary || "");
    const source = escapeHtml(item.source || "");
    const label = escapeHtml(item.label || "");
    const url = escapeHtml(item.url || "#");

    let dateText = "";
    if (item.published) {
      const d = new Date(item.published);
      dateText = Number.isNaN(d.getTime())
        ? escapeHtml(item.published)
        : d.toLocaleString("ja-JP");
    }

    return `
      <article class="card">
        <div class="meta">
          ${label ? `<span class="badge">${label}</span>` : ""}
          ${item.featured ? '<span class="star">★ 注目</span>' : ""}
          ${source ? `<span class="source">${source}</span>` : ""}
          ${dateText ? `<span class="source">${dateText}</span>` : ""}
        </div>

        <h3>${title}</h3>

        ${summary ? `<p>${summary}</p>` : ""}

        ${
          item.url
            ? `<a href="${url}" target="_blank" rel="noopener noreferrer">原文を見る ↗</a>`
            : ""
        }
      </article>
    `;
  }).join("");
}

async function loadNews() {
  const updatedAt = document.querySelector("#updatedAt");
  const newsEl = document.querySelector("#news");

  if (updatedAt) {
    updatedAt.textContent = "データ読み込み中…";
  }

  try {
    const response = await fetch(
      `${DATA_URL}?t=${Date.now()}`,
      { cache: "no-store" }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();

    allNews = Array.isArray(data.items) ? data.items : [];

    if (updatedAt) {
      if (data.updated_at) {
        const d = new Date(data.updated_at);

        updatedAt.textContent = Number.isNaN(d.getTime())
          ? `最終更新: ${data.updated_at}`
          : `最終更新: ${d.toLocaleString("ja-JP")}`;
      } else {
        updatedAt.textContent = `${allNews.length}件のニュースを取得`;
      }
    }

    renderNews();

  } catch (error) {
    console.error(error);

    if (updatedAt) {
      updatedAt.textContent = "ニュースの読み込みに失敗しました";
    }

    if (newsEl) {
      newsEl.innerHTML =
        '<div class="empty">データを取得できませんでした。</div>';
    }
  }
}

document.querySelector("#search")?.addEventListener("input", renderNews);

document.querySelector("#refreshBtn")?.addEventListener("click", loadNews);

renderFilters();
loadNews();

setInterval(loadNews, 15 * 60 * 1000);
