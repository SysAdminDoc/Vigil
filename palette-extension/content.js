(() => {
  if (window.__vigilPaletteContentInstalled) return;
  window.__vigilPaletteContentInstalled = true;

  const extensionOrigin = new URL(chrome.runtime.getURL('palette.html')).origin;
  let frame = null;
  let previousFocus = null;

  function restoreFocus() {
    if (previousFocus && document.contains(previousFocus)) {
      previousFocus.focus({preventScroll: true});
    }
    previousFocus = null;
  }

  function closePalette() {
    if (frame) frame.remove();
    frame = null;
    restoreFocus();
  }

  function focusPalette() {
    if (frame?.contentWindow) {
      frame.contentWindow.postMessage(
        {source: 'vigil-palette', type: 'focus'},
        extensionOrigin,
      );
    }
  }

  function openPalette() {
    if (frame) {
      focusPalette();
      return;
    }
    previousFocus = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;
    frame = document.createElement('iframe');
    frame.title = 'Vigil command palette';
    frame.tabIndex = -1;
    const parentOrigin = encodeURIComponent(window.location.origin);
    frame.src = chrome.runtime.getURL(
      `palette.html?embedded=1&parentOrigin=${parentOrigin}`,
    );
    Object.assign(frame.style, {
      all: 'initial',
      background: 'transparent',
      border: '0',
      height: '100%',
      inset: '0',
      margin: '0',
      padding: '0',
      position: 'fixed',
      width: '100%',
      zIndex: '2147483647',
    });
    frame.addEventListener('load', focusPalette, {once: true});
    document.documentElement.appendChild(frame);
    frame.focus({preventScroll: true});
  }

  chrome.runtime.onMessage.addListener((message) => {
    if (message?.type === 'open-palette') openPalette();
  });

  window.addEventListener('message', (event) => {
    if (!frame || event.source !== frame.contentWindow || event.origin !== extensionOrigin) {
      return;
    }
    if (event.data?.source === 'vigil-palette' && event.data.type === 'close') {
      closePalette();
    }
  });
})();
