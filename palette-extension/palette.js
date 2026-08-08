const params = new URLSearchParams(location.search);
const embedded = params.get('embedded') === '1';
const fallbackTabId = Number(params.get('tabId'));
const parentOrigin = (() => {
  if (!embedded) return '';
  try {
    const origin = new URL(params.get('parentOrigin') || '').origin;
    return /^https?:$/.test(new URL(origin).protocol) ? origin : '';
  } catch {
    return '';
  }
})();
const queryInput = document.getElementById('query');
const resultsList = document.getElementById('results');
const status = document.getElementById('status');
let results = [];
let selectedIndex = 0;
let searchTimer = null;
let searchSequence = 0;
let searchError = "";

function closePalette() {
  if (embedded && parentOrigin) {
    window.parent.postMessage({source: 'vigil-palette', type: 'close'}, parentOrigin);
  } else if (!embedded) {
    window.close();
  }
}

function kindLabel(kind) {
  return ({page: 'page', tab: 'tab', bookmark: 'bookmark', history: 'history'})[kind] || kind;
}

function render() {
  resultsList.replaceChildren();
  if (searchError) {
    status.textContent = searchError;
    queryInput.removeAttribute('aria-activedescendant');
    queryInput.setAttribute('aria-expanded', 'false');
    return;
  }
  if (!results.length) {
    status.textContent = 'No matching commands or saved pages.';
    queryInput.removeAttribute('aria-activedescendant');
    queryInput.setAttribute('aria-expanded', 'false');
    return;
  }
  queryInput.setAttribute('aria-expanded', 'true');
  status.textContent = `${results.length} result${results.length === 1 ? '' : 's'}`;
  results.forEach((item, index) => {
    const row = document.createElement('li');
    row.id = `palette-result-${index}`;
    row.className = 'result';
    row.tabIndex = -1;
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
  queryInput.setAttribute('aria-activedescendant', `palette-result-${selectedIndex}`);
}

async function search() {
  const sequence = ++searchSequence;
  searchError = "";
  queryInput.setAttribute('aria-busy', 'true');
  status.textContent = 'Searching…';
  try {
    const response = await chrome.runtime.sendMessage({
      type: 'palette-search',
      query: queryInput.value.slice(0, 200),
      requestId: sequence,
    });
    if (sequence !== searchSequence) return;
    if (!response?.ok) {
      results = [];
      searchError = 'Palette data is unavailable. Press Enter to retry.';
    } else {
      results = response.items || [];
      selectedIndex = 0;
      searchError = "";
    }
  } catch {
    if (sequence === searchSequence) {
      results = [];
      searchError = 'Palette data is unavailable. Press Enter to retry.';
    }
  } finally {
    if (sequence === searchSequence) {
      queryInput.removeAttribute('aria-busy');
      render();
    }
  }
}

async function openResult(item) {
  try {
    const response = await chrome.runtime.sendMessage({
      type: 'palette-open',
      url: item.url,
      tabId: Number.isInteger(fallbackTabId) && fallbackTabId > 0 ? fallbackTabId : undefined,
    });
    if (!response?.ok) {
      status.textContent = response?.error || 'Could not open that target.';
      return;
    }
    closePalette();
  } catch {
    status.textContent = 'Could not open that target. Retry.';
  }
}

queryInput.addEventListener('input', () => {
  searchError = "";
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
  } else if (event.key === 'Enter' && searchError) {
    event.preventDefault();
    search();
  } else if (event.key === 'Tab') {
    event.preventDefault();
    queryInput.focus();
  }
});

window.addEventListener('message', (event) => {
  if (!embedded || !parentOrigin || event.source !== window.parent || event.origin !== parentOrigin) {
    return;
  }
  if (event.data?.source === 'vigil-palette' && event.data.type === 'focus') {
    queryInput.focus();
    queryInput.select();
  }
});

queryInput.focus();
search();
