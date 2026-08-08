importScripts('i18n.js');

const t = (key, substitutions) => globalThis.vigilI18n?.getMessage(key, substitutions) || key;

const COMMAND_PAGES = [
  {title: t('commandSettings'), subtitle: t('urlSettings'), url: 'chrome://settings/'},
  {title: t('commandExtensions'), subtitle: t('urlExtensions'), url: 'chrome://extensions/'},
  {title: t('commandDownloads'), subtitle: t('urlDownloads'), url: 'chrome://downloads/'},
  {title: t('commandBookmarks'), subtitle: t('urlBookmarks'), url: 'chrome://bookmarks/'},
  {title: t('commandHistory'), subtitle: t('urlHistory'), url: 'chrome://history/'},
  {title: t('commandFlags'), subtitle: t('urlFlags'), url: 'chrome://flags/'},
  {title: t('commandPolicy'), subtitle: t('urlPolicy'), url: 'chrome://policy/'},
  {title: t('commandDiscards'), subtitle: t('urlDiscards'), url: 'chrome://discards/'},
  {title: t('commandNetworkInternals'), subtitle: t('urlNetworkInternals'), url: 'chrome://net-internals/'},
  {title: t('commandWebRtcInternals'), subtitle: t('urlWebRtcInternals'), url: 'chrome://webrtc-internals/'},
  {title: t('commandVersion'), subtitle: t('urlVersion'), url: 'chrome://version/'},
];

function isUsableUrl(url) {
  if (typeof url !== 'string' || url.length > 2048) return false;
  try {
    const parsed = new URL(url);
    return ['http:', 'https:', 'chrome:'].includes(parsed.protocol)
      && !parsed.username && !parsed.password;
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
        subtitle: t('bookmarkSubtitle'),
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
      subtitle: t('openTabSubtitle'),
      url: tab.url,
    }, normalized)) {
      items.push({
        kind: 'tab',
        title: tab.title || tab.url,
        subtitle: t('openTabSubtitle'),
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
        subtitle: t('bookmarkSubtitle'),
        url: node.url,
      });
    }
  }

  for (const item of historyItems) {
    if (item.url && isUsableUrl(item.url) && matches({
      title: item.title || item.url,
      subtitle: t('historySubtitle'),
      url: item.url,
    }, normalized)) {
      items.push({
        kind: 'history',
        title: item.title || item.url,
        subtitle: t('historySubtitle'),
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
  if (!message || typeof message !== 'object') {
    return {ok: false, error: t('invalidTarget')};
  }
  if (!isUsableUrl(message.url)) return {ok: false, error: t('unsupportedTarget')};
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

async function openInjectedPalette(tabId) {
  try {
    await chrome.tabs.sendMessage(tabId, {type: 'open-palette'});
    return;
  } catch {
    // The activeTab grant is used to inject only after the user invokes the command.
  }
  await chrome.scripting.executeScript({target: {tabId}, files: ['content.js']});
  await chrome.tabs.sendMessage(tabId, {type: 'open-palette'});
}

chrome.commands.onCommand.addListener(async (command) => {
  if (command !== 'open-palette') return;
  const [tab] = await chrome.tabs.query({active: true, lastFocusedWindow: true});
  if (!tab || !Number.isInteger(tab.id)) return;
  if (tab.url && /^https?:/i.test(tab.url)) {
    try {
      await openInjectedPalette(tab.id);
      return;
    } catch {
      // Content scripts cannot run on every browser-owned page.
    }
  }
  await openPaletteTab(tab.id);
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === 'palette-search') {
    const query = typeof message.query === 'string' ? message.query.slice(0, 200) : '';
    searchPalette(query)
        .then((items) => sendResponse({ok: true, items, requestId: message.requestId}))
        .catch((error) => sendResponse({ok: false, error: String(error), requestId: message.requestId}));
    return true;
  }
  if (message?.type === 'palette-open') {
    openTarget(message, sender)
        .then(sendResponse)
        .catch((error) => sendResponse({ok: false, error: String(error)}));
    return true;
  }
  return false;
});
