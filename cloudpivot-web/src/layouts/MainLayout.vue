<template>
  <t-layout class="main-layout">
    <t-aside :width="collapsed ? '64px' : '232px'" :collapsed="collapsed">
      <div class="logo">
        <t-icon name="control-platform" class="logo-icon" />
        <span v-show="!collapsed" class="logo-text">CloudPivot</span>
      </div>
      <t-menu
        :value="currentRoute"
        :collapsed="collapsed"
        @change="onMenuChange"
      >
        <t-menu-item value="/dashboard">
          <template #icon><t-icon name="dashboard" /></template>
          {{ $t('menu.dashboard') }}
        </t-menu-item>
        <t-menu-item value="/hosts">
          <template #icon><t-icon name="server" /></template>
          {{ $t('menu.hosts') }}
        </t-menu-item>
        <t-menu-item value="/terminal">
          <template #icon><t-icon name="root-list" /></template>
          {{ $t('menu.terminal') }}
        </t-menu-item>
        <t-menu-item value="/teams">
          <template #icon><t-icon name="usergroup" /></template>
          {{ $t('menu.teams') }}
        </t-menu-item>
        <t-menu-item value="/permissions">
          <template #icon><t-icon name="lock-on" /></template>
          {{ $t('menu.permissions') }}
        </t-menu-item>
        <t-menu-item value="/audit">
          <template #icon><t-icon name="file-copy" /></template>
          {{ $t('menu.audit') }}
        </t-menu-item>
        <t-menu-item value="/monitor">
          <template #icon><t-icon name="chart-bar" /></template>
          {{ $t('menu.monitor') }}
        </t-menu-item>
        <t-menu-item value="/docker">
          <template #icon><t-icon name="control-platform" /></template>
          {{ $t('menu.docker') }}
        </t-menu-item>
        <t-menu-item value="/alerts">
          <template #icon><t-icon name="error-circle" /></template>
          {{ $t('menu.alerts') }}
        </t-menu-item>
        <t-menu-item value="/settings">
          <template #icon><t-icon name="setting" /></template>
          {{ $t('menu.settings') }}
        </t-menu-item>
        <t-menu-item v-if="isAdmin" value="/users">
          <template #icon><t-icon name="user" /></template>
          {{ $t('settings.userManagement') }}
        </t-menu-item>
      </t-menu>
    </t-aside>
    <t-layout>
      <t-header class="main-header">
        <div class="header-left">
          <t-button variant="text" @click="appStore.toggleSidebar">
            <t-icon :name="collapsed ? 'chevron-right' : 'chevron-left'" />
          </t-button>
          <t-breadcrumb>
            <t-breadcrumb-item>{{ $t(`menu.${currentMenuKey}`) }}</t-breadcrumb-item>
          </t-breadcrumb>
        </div>
        <div class="header-right">
          <t-button variant="text" @click="appStore.toggleTheme">
            <t-icon :name="appStore.theme === 'dark' ? 'sunny' : 'moon'" />
          </t-button>
          <t-dropdown :options="langOptions" @click="onLangChange">
            <t-button variant="text">
              <t-icon name="translate" />
            </t-button>
          </t-dropdown>
          <t-dropdown :options="userOptions" @click="onUserAction">
            <t-button variant="text">
              <t-icon name="user-circle" />
              <span style="margin-left: 4px">{{ userStore.userInfo?.username || 'User' }}</span>
            </t-button>
          </t-dropdown>
        </div>
      </t-header>
      <t-content class="main-content">
        <router-view />
      </t-content>
    </t-layout>
  </t-layout>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useAppStore, useUserStore } from '@/stores/app';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();
const router = useRouter();
const route = useRoute();
const appStore = useAppStore();
const userStore = useUserStore();
const { locale } = useI18n();

const collapsed = computed(() => appStore.collapsed);
const currentRoute = computed(() => route.path);
const currentMenuKey = computed(() => {
  const path = route.path.split('/')[1];
  return path || 'dashboard';
});
const isAdmin = computed(() => userStore.userInfo?.role === 'admin');

const langOptions = [
  { content: '中文', value: 'zh-CN' },
  { content: 'English', value: 'en' },
];

const userOptions = [
  { content: t('settings.profile'), value: 'profile' },
  { content: t('settings.logout'), value: 'logout' },
];

function onMenuChange(value: string) {
  router.push(value);
}

function onLangChange(data: any) {
  const lang = data.value as 'zh-CN' | 'en';
  appStore.setLocale(lang);
  locale.value = lang;
}

function onUserAction(data: any) {
  if (data.value === 'logout') {
    userStore.logout();
    router.push('/login');
  } else if (data.value === 'profile') {
    router.push('/settings');
  }
}
</script>

<style scoped>
.main-layout {
  height: 100vh;
}
.logo {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 64px;
  padding: 0 16px;
  gap: 8px;
  border-bottom: 1px solid var(--td-border-level-1-color);
}
.logo-icon {
  font-size: 28px;
  color: var(--td-brand-color);
}
.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: var(--td-brand-color);
  white-space: nowrap;
}
.main-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 64px;
  border-bottom: 1px solid var(--td-border-level-1-color);
}
.header-left,
.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.main-content {
  padding: 24px;
  overflow-y: auto;
  background: var(--td-bg-page-container);
}
</style>
