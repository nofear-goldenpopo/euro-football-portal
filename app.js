const DATA_URL = "./data/news.json";

const state = {
  items: [],
  query: ""
};

const els = {
  status: document.querySelector("#status"),
  newsList: document.querySelector("#newsList"),
  search: document.querySelector("#search"),
  refresh: document.querySelector("#refresh")
};

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("ja-JP", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

function filteredItems() {
  const q = state.query.trim().toLowerCase();

  if (!q) return state.items;

  return state.items.filter(item => {
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

    return text.includes(q);
  });
}

function render() {
  if (!els.newsList) return;

  const items = filteredItems();

  if (!items.length) {
    els.newsList.innerHTML =
      '<p class="empty">該当するニュースがありません。</p>';
    return;
  }

  els.newsList.innerHTML = items.map(item => {
    const title = escapeHtml(item.title || "タイトルなし");
    const summary = escapeHtml(item.summary || "");
    const source = escapeHtml(item.source || "");
    const label = escapeHtml(item.label || "");
    const date = escapeHtml(formatDate(item.published));
    const url = escapeHtml(item.url || "#");

    return `
      <article class="news-card">
        <div class="news-meta">
          ${label ? `<span>${label}</span>` : ""}
          ${source ? `<span>${source}</span>` : ""}
          ${date ? `<span>${date}</span>` : ""}
        </div>

        <h2 class="news-title">
          <a href="${url}" target="_blank" rel="noopener noreferrer">
            ${title}
          </a>
        </h2>

        ${summary ? `<p class="news-summary">${summary}</p>` : ""}
      </article>
    `;
  }).join("");
}

async function loadNews() {
  if (els.status) {
    els.status.textContent = "データ読み込み中…";
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

    state.items = Array.isArray(data.items) ? data.items : [];

    if (els.status) {
      if (state.items.length) {
        els.status.textContent =
          `${state.items.length}件のニュースを取得`;
      } else {
        els.status.textContent =
          "ニュースデータは現在0件です";
      }
    }

    render();

  } catch (error) {
    console.error(error);

    if (els.status) {
      els.status.textContent =
        "ニュースの読み込みに失敗しました";
    }

    if (els.newsList) {
      els.newsList.innerHTML =
        '<p class="empty">データを取得できませんでした。</p>';
    }
  }
}

if (els.search) {
  els.search.addEventListener("input", event => {
    state.query = event.target.value;
    render();
  });
}

if (els.refresh) {
  els.refresh.addEventListener("click", loadNews);
}

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") {
    loadNews();
  }
});

loadNews();

setInterval(loadNews, 15 * 60 * 1000);
