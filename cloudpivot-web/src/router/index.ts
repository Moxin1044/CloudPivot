import { createRouter, createWebHistory } from 'vue-router';
import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { title: '登录', noAuth: true },
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: { title: 'Dashboard', icon: 'dashboard' },
      },
      {
        path: 'hosts',
        name: 'Hosts',
        component: () => import('@/views/host/index.vue'),
        meta: { title: '主机资产', icon: 'server' },
      },
      {
        path: 'hosts/:id',
        name: 'HostDetail',
        component: () => import('@/views/host/detail.vue'),
        meta: { title: '主机详情', hidden: true },
      },
      {
        path: 'terminal',
        name: 'Terminal',
        component: () => import('@/views/terminal/index.vue'),
        meta: { title: 'WebSSH', icon: 'root-list' },
      },
      {
        path: 'sftp',
        name: 'SFTP',
        component: () => import('@/views/sftp/index.vue'),
        meta: { title: 'SFTP', icon: 'folder-open' },
      },
      {
        path: 'teams',
        name: 'Teams',
        component: () => import('@/views/team/index.vue'),
        meta: { title: '团队管理', icon: 'usergroup' },
      },
      {
        path: 'permissions',
        name: 'Permissions',
        component: () => import('@/views/permission/index.vue'),
        meta: { title: '权限管理', icon: 'lock-on' },
      },
      {
        path: 'audit',
        name: 'Audit',
        component: () => import('@/views/audit/index.vue'),
        meta: { title: '会话审计', icon: 'file-copy' },
      },
      {
        path: 'monitor',
        name: 'Monitor',
        component: () => import('@/views/monitor/index.vue'),
        meta: { title: '主机监控', icon: 'chart-bar' },
      },
      {
        path: 'alerts',
        name: 'Alerts',
        component: () => import('@/views/alert/index.vue'),
        meta: { title: '告警中心', icon: 'error-circle' },
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/settings/index.vue'),
        meta: { title: '系统设置', icon: 'setting' },
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/user/index.vue'),
        meta: { title: '用户管理', icon: 'user', adminOnly: true },
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('token');
  if (!to.meta.noAuth && !token) {
    next({ name: 'Login' });
    return;
  }
  if (to.meta.adminOnly) {
    const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}');
    if (userInfo.role !== 'admin') {
      next({ path: '/' });
      return;
    }
  }
  next();
});

export default router;
