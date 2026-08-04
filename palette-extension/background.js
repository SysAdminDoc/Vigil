const COMMAND_PAGES = [
  {title: 'Settings', subtitle: 'chrome://settings', url: 'chrome://settings/'},
  {title: 'Extensions', subtitle: 'chrome://extensions', url: 'chrome://extensions/'},
  {title: 'Downloads', subtitle: 'chrome://downloads', url: 'chrome://downloads/'},
  {title: 'Bookmarks', subtitle: 'chrome://bookmarks', url: 'chrome://bookmarks/'},
  {title: 'History', subtitle: 'chrome://history', url: 'chrome://history/'},
  {title: 'Flags', subtitle: 'chrome://flags', url: 'chrome://flags/'},
  {title: 'Policy', subtitle: 'chrome://policy', url: 'chrome://policy/'},
  {title: 'Discards', subtitle: 'chrome://discards', url: 'chrome://discards/'},
  {title: 'Network internals', subtitle: 'chrome://net-internals', url: 'chrome://net-internals/'},
  {title: 'WebRTC internals', subtitle: 'chrome://webrtc-internals', url: 'chrome://webrtc-internals/'},
  {title: 'Version', subtitle: 'chrome://version', url: 'chrome://version/'},
];

function isUsableUrl(url) {
  if (!url) return false;
  try {
    const parsed = new URL(url);
    return ['http:', 'https:', 'chrome:', 'file:'].includes(parsed.protocol);
  } catch {
    return false;
  }
}

function matches(item, query) {
  if (!query) return true;
  const haystack = `${item.title} ${item.subtitle} ${item.url}`.toLowerCase();
  return haystack.includes(query.toLowerCase());
}

function flattenBookmarks(nodes, result) {
  for (const node of nodes) {
    if (node.url && isUsableUrl(node.url)) {
      result.push({
        kind: 'bookmark',
        title: node.title || node.url,
        subtitle: 'Bookmark',
        url: node.url,
      });
    }
    if (node.children) flattenBookmarks(node.children, result);
  }
}

async function getBookmarks(query) {
  if (query) return chrome.bookmarks.search({query});
  return chrome.bookmarks.getTree();
}

async function searchPalette(query) {
  const normalized = (query || '').trim();
  const [tabs, bookmarkNodes, historyItems] = await Promise.all([
    chrome.tabs.query({}),
    getBookmarks(normalized),
    chrome.history.search({
      text: normalized,
      startTime: Date.now() - 7 * 24 * 60 * 60 * 1000,
      maxResults: 40,
    }),
  ]);

  const items = COMMAND_PAGES
      .filter((item) => matches(item, normalized))
      .map((item) => ({...item, kind: 'page'}));

  for (const tab of tabs) {
    if (tab.url && isUsableUrl(tab.url) && matches({
      title: tab.title || tab.url,
      subtitle: 'Open tab',
      url: tab.url,
    }, normalized)) {
      items.push({
        kind: 'tab',
        title: tab.title || tab.url,
        subtitle: 'Open tab',
        url: tab.url,
        tabId: tab.id,
      });
    }
  }

  const bookmarks = [];
  if (normalized) {
    for (const node of bookmarkNodes) {
      if (node.url) bookmarks.push(node);
    }
  } else {
    flattenBookmarks(bookmarkNodes, bookmarks);
  }
  for (const node of bookmarks.slice(0, 30)) {
    if (node.url && isUsableUrl(node.url)) {
      items.push({
        kind: 'bookmark',
        title: node.title || node.url,
        subtitle: 'Bookmark',
        url: node.url,
      });
    }
  }

  for (const item of historyItems) {
    if (item.url && isUsableUrl(item.url) && matches({
      title: item.title || item.url,
      subtitle: 'History · last 7 days',
      url: item.url,
    }, normalized)) {
      items.push({
        kind: 'history',
        title: item.title || item.url,
        subtitle: 'History · last 7 days',
        url: item.url,
      });
    }
  }

  const seen = new Set();
  return items.filter((item) => {
    const key = `${item.kind}:${item.url}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  }).slice(0, 100);
}

async function openTarget(message, sender) {
  if (!isUsableUrl(message.url)) return {ok: false, error: 'Unsupported target'};
  const senderTabId = sender.tab && sender.tab.id;
  const tabId = Number.isInteger(message.tabId) ? message.tabId : senderTabId;
  if (Number.isInteger(tabId)) {
    try {
      await chrome.tabs.update(tabId, {url: message.url, active: true});
      return {ok: true};
    } catch {
      // The original tab may have closed while the palette was open.
    }
  }
  await chrome.tabs.create({url: message.url});
  return {ok: true};
}

async function openPaletteTab(tabId) {
  const query = Number.isInteger(tabId) ? `?tabId=${tabId}` : '';
  await chrome.tabs.create({
    url: chrome.runtime.getURL(`palette.html${query}`),
  });
}

chrome.commands.onCommand.addListener(async (command) => {
  if (command !== 'open-palette') return;
  const [tab] = await chrome.tabs.query({active: true, lastFocusedWindow: true});
  if (!tab || !Number.isInteger(tab.id)) return;
  if (tab.url && /^https?:/i.test(tab.url)) {
    try {
      await chrome.tabs.sendMessage(tab.id, {type: 'open-palette'});
      return;
    } catch {
      // Content scripts cannot run on every browser-owned page.
    }
  }
  await openPaletteTab(tab.id);
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'palette-search') {
    searchPalette(message.query || '')
        .then((items) => sendResponse({ok: true, items}))
        .catch((error) => sendResponse({ok: false, error: String(error)}));
    return true;
  }
  if (message.type === 'palette-open') {
    openTarget(message, sender)
        .then(sendResponse)
        .catch((error) => sendResponse({ok: false, error: String(error)}));
    return true;
  }
  return false;
});
