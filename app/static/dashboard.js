// Keeps the running figures current while a session is open. The server-rendered
// values stay as they are without JavaScript.
(() => {
  const loaded = Date.now();
  const pad = (value) => String(value).padStart(2, '0');
  const items = Array.from(document.querySelectorAll('[data-live]'), (element) => {
    const item = { element, base: Number(element.dataset.live), withSeconds: element.dataset.liveFormat === 'hms' };
    if (item.withSeconds) {
      item.minutes = document.createTextNode('');
      item.seconds = document.createElement('span');
      item.seconds.className = 'clock-seconds';
      item.seconds.setAttribute('aria-hidden', 'true');
      element.replaceChildren(item.minutes, item.seconds);
    }
    return item;
  }).filter((item) => Number.isFinite(item.base));
  if (!items.length) return;

  const render = () => {
    const elapsed = Math.max(0, Math.floor((Date.now() - loaded) / 1000));
    for (const item of items) {
      const total = item.base + elapsed;
      if (item.withSeconds) {
        item.minutes.nodeValue = `${Math.floor(total / 3600)}h${pad(Math.floor((total % 3600) / 60))}`;
        item.seconds.textContent = pad(total % 60);
      } else {
        const minutes = Math.round(total / 60);
        item.element.textContent = `${Math.floor(minutes / 60)}h${pad(minutes % 60)}`;
      }
    }
  };
  render();
  setInterval(render, 1000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) render(); });
})();
