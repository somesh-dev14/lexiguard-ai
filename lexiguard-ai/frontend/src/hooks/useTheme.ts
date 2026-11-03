import { useState, useEffect } from 'react';

type Theme = 'light' | 'dark' | 'system';

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => {
    const stored = localStorage.getItem('lexiguard_theme');
    return (stored as Theme) || 'light';
  });
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const root = document.documentElement;
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const apply = (t: Theme) => {
      const dark = t === 'dark' || (t === 'system' && mq.matches);
      setIsDark(dark);
      root.classList.toggle('dark', dark);
    };
    apply(theme);
    localStorage.setItem('lexiguard_theme', theme);
    if (theme === 'system') {
      const handler = () => apply('system');
      mq.addEventListener('change', handler);
      return () => mq.removeEventListener('change', handler);
    }
  }, [theme]);

  return { theme, setTheme, isDark };
}
