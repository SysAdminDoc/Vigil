const params = new URLSearchParams(location.search);
const embedded = params.get('embedded') === '1';
const fallbackTabId = Number(params.get('tabId'));
const queryInput = document.getElementById('query');
const resultsList = document.getElementById('results');
const status = document.getElementById('status');
let results = [];
let selectedIndex = 0;
let searchTimer = null;

function closePalette() {
  if (embedded) {
    window.parent.postMessage({source: 'vigil-palette', type: 'close'}, '*');
  } else {
    window.close();
  }
}

function kindLabel(kind) {
  return ({page: 'page', tab: 'tab', bookmark: 'bookmark', history: 'history'})[kind] || kind;
}

function render() {
  resultsList.replaceChildren();
  if (!results.length) {
    status.textContent = 'No matching commands or saved pages.';
    return;
  }
  status.textContent = `${results.length} result${results.length === 1 ? '' : 's'}`;
  results.forEach((item, index) => {
    const row = document.createElement('li');
    row.className = 'result';
    row.setAttribute('role', 'option');
    row.setAttribute('aria-selected', String(index === selectedIndex));
    row.addEventListener('mouseenter', () => {
      selectedIndex = index;
      render();
    });
    row.addEventListener('click', () => openResult(item));

    const main = document.createElement('div');
    main.className = 'result-main';
    const title = document.createElement('div');
    title.className = 'result-title';
    title.textContent = item.title;
    const subtitle = document.createElement('div');
    subtitle.className = 'result-subtitle';
    subtitle.textContent = item.subtitle || item.url;
    main.append(title, subtitle);

    const kind = document.createElement('div');
    kind.className = 'result-kind';
    kind.textContent = kindLabel(item.kind);
    row.append(main, kind);
    resultsList.append(row);
  });
}

async function search() {
  const response = await chrome.runtime.sendMessage({
    type: 'palette-search',
    query: queryInput.value,
  });
  if (!response?.ok) {
    results = [];
    status.textContent = 'Palette data is unavailable in this profile.';
  } else {
    results = response.items || [];
    selectedIndex = Math.min(selectedIndex, Math.max(results.length - 1, 0));
  }
  render();
}

async function openResult(item) {
  await chrome.runtime.sendMessage({
    type: 'palette-open',
    url: item.url,
    tabId: Number.isInteger(fallbackTabId) && fallbackTabId > 0 ? fallbackTabId : undefined,
  });
  closePalette();
}

queryInput.addEventListener('input', () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(search, 80);
});

queryInput.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') {
    event.preventDefault();
    closePalette();
  } else if (event.key === 'ArrowDown') {
    event.preventDefault();
    selectedIndex = Math.min(selectedIndex + 1, Math.max(results.length - 1, 0));
    render();
  } else if (event.key === 'ArrowUp') {
    event.preventDefault();
    selectedIndex = Math.max(selectedIndex - 1, 0);
    render();
  } else if (event.key === 'Enter' && results[selectedIndex]) {
    event.preventDefault();
    openResult(results[selectedIndex]);
  }
});

window.addEventListener('message', (event) => {
  if (event.data?.source !== 'vigil-palette' || event.data.type !== 'focus') return;
  queryInput.focus();
  queryInput.select();
});

queryInput.focus();
search();
