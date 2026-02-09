const STORAGE_KEY = 'theme';

function applyTheme() {
  const stored = localStorage.getItem(STORAGE_KEY);
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const shouldBeDark = stored === 'dark' || (stored !== 'light' && prefersDark);

  document.documentElement.classList.toggle('dark', shouldBeDark);
}

export function initTheme() {
  applyTheme();
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored || stored === 'system') {
      applyTheme();
    }
  });
}

export function setTheme(mode) {
  if (mode === 'system') {
    localStorage.removeItem(STORAGE_KEY);
  } else {
    localStorage.setItem(STORAGE_KEY, mode);
  }
  applyTheme();
}

export function getTheme() {
  return localStorage.getItem(STORAGE_KEY) || 'system';
}
