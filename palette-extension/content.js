(() => {
  let frame = null;

  function closePalette() {
    if (frame) frame.remove();
    frame = null;
  }

  function openPalette() {
    if (frame) {
      frame.contentWindow?.postMessage({source: 'vigil-palette', type: 'focus'}, '*');
      return;
    }
    frame = document.createElement('iframe');
    frame.title = 'Vigil command palette';
    frame.src = chrome.runtime.getURL('palette.html?embedded=1');
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
    document.documentElement.appendChild(frame);
  }

  chrome.runtime.onMessage.addListener((message) => {
    if (message.type === 'open-palette') openPalette();
  });

  window.addEventListener('message', (event) => {
    if (!frame || event.source !== frame.contentWindow ||
        event.data?.source !== 'vigil-palette') return;
    if (event.data.type === 'close') closePalette();
  });
})();
