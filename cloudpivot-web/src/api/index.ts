import axios from 'axios';
import { MessagePlugin } from 'tdesign-vue-next';
import { useUserStore } from '@/stores/app';
import router from '@/router';

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
});

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error.response?.status;
    const detail = error.response?.data?.detail || '请求失败';

    if (status === 401) {
      const userStore = useUserStore();
      userStore.logout();
      router.push('/login');
      MessagePlugin.error('登录已过期，请重新登录');
    } else if (status === 403) {
      MessagePlugin.error('无权限访问');
    } else if (status === 404) {
      MessagePlugin.error('资源不存在');
    } else {
      MessagePlugin.error(detail);
    }

    return Promise.reject(error);
  }
);

export default request;

// ===== Auth API =====
export const authApi = {
  login: (data: { username: string; password: string }) => request.post('/auth/login', data),
  register: (data: any) => request.post('/auth/register', data),
  refresh: (data: { refresh_token: string }) => request.post('/auth/refresh', data),
  getMe: () => request.get('/users/me'),
  updateMe: (data: any) => request.put('/users/me', data),
  updateNotifications: (data: any) => request.put('/users/me/notifications', data),
  changePassword: (data: any) => request.put('/users/me/password', data),
};

// ===== Users API =====
export const userApi = {
  list: (params?: any) => request.get('/users', { params }),
  create: (data: any) => request.post('/users', data),
  get: (id: number) => request.get(`/users/${id}`),
  update: (id: number, data: any) => request.put(`/users/${id}`, data),
  delete: (id: number) => request.delete(`/users/${id}`),
};

// ===== Hosts API =====
export const hostApi = {
  list: (params?: any) => request.get('/hosts', { params }),
  create: (data: any) => request.post('/hosts', data),
  get: (id: number) => request.get(`/hosts/${id}`),
  update: (id: number, data: any) => request.put(`/hosts/${id}`, data),
  delete: (id: number) => request.delete(`/hosts/${id}`),
  testConnectivity: (id: number) => request.post(`/hosts/${id}/test`),
  batchImport: (data: any) => request.post('/hosts/batch-import', data),
  listGroups: () => request.get('/hosts/groups/list'),
  createGroup: (data: any) => request.post('/hosts/groups', data),
  listTags: () => request.get('/hosts/tags/list'),
  createTag: (data: any) => request.post('/hosts/tags', data),
};

// ===== Teams API =====
export const teamApi = {
  list: (params?: any) => request.get('/teams', { params }),
  create: (data: any) => request.post('/teams', data),
  get: (id: number) => request.get(`/teams/${id}`),
  update: (id: number, data: any) => request.put(`/teams/${id}`, data),
  delete: (id: number) => request.delete(`/teams/${id}`),
  listMembers: (id: number) => request.get(`/teams/${id}/members`),
  addMember: (id: number, data: any) => request.post(`/teams/${id}/members`, data),
  updateMember: (teamId: number, userId: number, data: any) =>
    request.put(`/teams/${teamId}/members/${userId}`, data),
  removeMember: (teamId: number, userId: number) =>
    request.delete(`/teams/${teamId}/members/${userId}`),
};

// ===== Permissions API =====
export const permissionApi = {
  list: (params?: any) => request.get('/permissions', { params }),
  create: (data: any) => request.post('/permissions', data),
  update: (id: number, data: any) => request.put(`/permissions/${id}`, data),
  delete: (id: number) => request.delete(`/permissions/${id}`),
  listTemporary: (params?: any) => request.get('/permissions/temporary', { params }),
  createTemporary: (data: any) => request.post('/permissions/temporary', data),
  revokeTemporary: (id: number) => request.post(`/permissions/temporary/${id}/revoke`),
};

// ===== Sessions/Audit API =====
export const sessionApi = {
  list: (params?: any) => request.get('/sessions', { params }),
  getCommands: (sessionId: number, params?: any) =>
    request.get(`/sessions/${sessionId}/commands`, { params }),
  getRecording: (sessionId: number) => request.get(`/sessions/${sessionId}/recording`),
  getActive: () => request.get('/active-sessions'),
};

// ===== Audit API =====
export const auditApi = {
  listSessions: (params?: any) => request.get('/audit/sessions', { params }),
  listCommands: (params?: any) => request.get('/audit/commands', { params }),
  listLoginLogs: (params?: any) => request.get('/audit/login-logs', { params }),
  listRiskCommands: (params?: any) => request.get('/audit/risk-commands', { params }),
  exportCommands: (params?: any) => request.get('/audit/export/commands', { params }),
};

// ===== Monitor API =====
export const monitorApi = {
  getMetrics: (hostId: number, hours?: number) =>
    request.get(`/monitor/metrics/${hostId}`, { params: { hours } }),
  getLatestMetric: (hostId: number) => request.get(`/monitor/metrics/${hostId}/latest`),
  listAlertRules: () => request.get('/monitor/alert-rules'),
  createAlertRule: (data: any) => request.post('/monitor/alert-rules', data),
  updateAlertRule: (id: number, data: any) => request.put(`/monitor/alert-rules/${id}`, data),
  deleteAlertRule: (id: number) => request.delete(`/monitor/alert-rules/${id}`),
  listAlerts: (params?: any) => request.get('/monitor/alerts', { params }),
  acknowledgeAlert: (id: number) => request.post(`/monitor/alerts/${id}/acknowledge`),
  resolveAlert: (id: number) => request.post(`/monitor/alerts/${id}/resolve`),
};

// ===== Docker API =====
export const dockerApi = {
  listHosts: () => request.get('/docker/hosts'),
  createHost: (data: any) => request.post('/docker/hosts', data),
  deleteHost: (id: number) => request.delete(`/docker/hosts/${id}`),
  listContainers: (all?: boolean) => request.get('/docker/containers', { params: { all } }),
  getContainer: (id: string) => request.get(`/docker/containers/${id}`),
  startContainer: (id: string) => request.post(`/docker/containers/${id}/start`),
  stopContainer: (id: string, timeout?: number) =>
    request.post(`/docker/containers/${id}/stop`, { timeout }),
  restartContainer: (id: string, timeout?: number) =>
    request.post(`/docker/containers/${id}/restart`, { timeout }),
  removeContainer: (id: string, force?: boolean) =>
    request.delete(`/docker/containers/${id}`, { params: { force } }),
  getContainerLogs: (id: string, tail?: number) =>
    request.get(`/docker/containers/${id}/logs`, { params: { tail } }),
  getContainerStats: (id: string) => request.get(`/docker/containers/${id}/stats`),
  execInContainer: (id: string, command: string, tty?: boolean) =>
    request.post(`/docker/containers/${id}/exec`, { command, tty }),
  listImages: () => request.get('/docker/images'),
  pullImage: (repository: string, tag?: string) =>
    request.post('/docker/images/pull', null, { params: { repository, tag } }),
  removeImage: (id: string, force?: boolean) =>
    request.delete(`/docker/images/${id}`, { params: { force } }),
  getInfo: () => request.get('/docker/info'),
};

// ===== Dashboard API =====
export const dashboardApi = {
  getOverview: () => request.get('/dashboard'),
};
