import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useAppStore = defineStore('app', () => {
  const theme = ref<'light' | 'dark'>('light');
  const locale = ref<'zh-CN' | 'en'>('zh-CN');
  const collapsed = ref(false);

  function initTheme() {
    const saved = localStorage.getItem('theme') as 'light' | 'dark' | null;
    if (saved) {
      theme.value = saved;
    } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      theme.value = 'dark';
    }
    document.documentElement.setAttribute('theme-mode', theme.value);
  }

  function toggleTheme() {
    theme.value = theme.value === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('theme-mode', theme.value);
    localStorage.setItem('theme', theme.value);
  }

  function initLocale() {
    const saved = localStorage.getItem('locale') as 'zh-CN' | 'en' | null;
    if (saved) locale.value = saved;
  }

  function setLocale(l: 'zh-CN' | 'en') {
    locale.value = l;
    localStorage.setItem('locale', l);
  }

  function toggleSidebar() {
    collapsed.value = !collapsed.value;
  }

  return { theme, locale, collapsed, initTheme, toggleTheme, initLocale, setLocale, toggleSidebar };
});

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '');
  const refreshToken = ref(localStorage.getItem('refreshToken') || '');
  const userInfo = ref<any>(null);

  function setTokens(access: string, refresh: string) {
    token.value = access;
    refreshToken.value = refresh;
    localStorage.setItem('token', access);
    localStorage.setItem('refreshToken', refresh);
  }

  function setUser(info: any) {
    userInfo.value = info;
  }

  async function logout() {
    try {
      // Notify backend to blacklist token
      await fetch('/api/v1/auth/logout', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token.value}`,
        },
      });
    } catch {
      // Ignore network errors during logout
    }
    clearAuth();
  }

  function clearAuth() {
    token.value = '';
    refreshToken.value = '';
    userInfo.value = null;
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('userInfo');
  }

  return { token, refreshToken, userInfo, setTokens, setUser, logout, clearAuth };
});
