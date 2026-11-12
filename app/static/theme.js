/* Local presentation preference only; no account or record changes. */
(() => {
  const button = document.querySelector('.theme-switch');
  if (!button) return;
  const systemTheme = matchMedia('(prefers-color-scheme: dark)');
  function savedTheme() {
    try { return localStorage.getItem('management-theme'); } catch (_) { return null; }
  }
  function apply(theme) {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    button.setAttribute('aria-pressed', String(theme === 'dark'));
    const root = document.documentElement.dataset;
    document.querySelector('meta[name="theme-color"]').content = (theme === 'dark' ? root.chromeDark : root.chromeLight) || '#173f38';
  }
  apply(document.documentElement.dataset.theme || (systemTheme.matches ? 'dark' : 'light'));
  button.hidden = false;
  button.addEventListener('click', () => {
    const theme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    try { localStorage.setItem('management-theme', theme); } catch (_) {}
    apply(theme);
  });
  systemTheme.addEventListener('change', event => {
    if (!['light', 'dark'].includes(savedTheme())) apply(event.matches ? 'dark' : 'light');
  });
  window.addEventListener('storage', event => {
    if (event.key === 'management-theme' || event.key === null) {
      const theme = savedTheme();
      apply(['light', 'dark'].includes(theme) ? theme : (systemTheme.matches ? 'dark' : 'light'));
    }
  });
})();
