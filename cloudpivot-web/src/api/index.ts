import axios from 'axios';
import { MessagePlugin } from 'tdesign-vue-next';
import { useUserStore } from '@/stores/app';
import router from '@/router';

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
});

// Token refresh state (avoid concurrent refresh calls)
let isRefreshing = false;
let refreshQueue: Array<{ resolve: (token: string) => void; reject: (err: any) => void }> = [];

function processRefreshQueue(token: string | null, error: any = null) {
  refreshQueue.forEach(({ resolve, reject }) => {
    if (token) resolve(token);
    else reject(error);
  });
  refreshQueue = [];
}

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

request.interceptors.response.use(
  (response) => response.data,
  async (error) => {
    const status = error.response?.status;
    const detail = error.response?.data?.detail || '请求失败';
    const originalRequest = error.config;

    if (status === 401 && !originalRequest._retry) {
      // Try token refresh
      const refreshToken = localStorage.getItem('refreshToken');
      if (refreshToken && originalRequest.url !== '/auth/login' && originalRequest.url !== '/auth/refresh') {
        if (isRefreshing) {
          // Queue requests while refreshing
          return new Promise((resolve, reject) => {
            refreshQueue.push({
              resolve: (token: string) => {
                originalRequest.headers.Authorization = `Bearer ${token}`;
                resolve(request(originalRequest));
              },
              reject,
            });
          });
        }

        originalRequest._retry = true;
        isRefreshing = true;

        try {
          const res: any = await axios.post('/api/v1/auth/refresh', { refresh_token: refreshToken });
          const newToken = res.data?.access_token || res.access_token;
          const newRefreshToken = res.data?.refresh_token || res.refresh_token;

          if (newToken) {
            localStorage.setItem('token', newToken);
            if (newRefreshToken) localStorage.setItem('refreshToken', newRefreshToken);
            processRefreshQueue(newToken);
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
            return request(originalRequest);
          }
        } catch (refreshError) {
          processRefreshQueue(null, refreshError);
          const userStore = useUserStore();
          userStore.logout();
          router.push('/login');
          MessagePlugin.error('登录已过期，请重新登录');
          return Promise.reject(refreshError);
        } finally {
          isRefreshing = false;
        }
      }

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
  login: (data: { username: string; password: string; captcha_id?: string; captcha_code?: string }) =>
    request.post('/auth/login', data),
  register: (data: any) => request.post('/auth/register', data),
  refresh: (data: { refresh_token: string }) => request.post('/auth/refresh', data),
  logout: () => request.post('/auth/logout'),
  getCaptcha: () => request.get('/auth/captcha'),
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

export const siteConfigApi = {
  list: () => request.get('/site-config'),
  update: (key: string, data: any) => request.put(`/site-config/${key}`, data),
  batchUpdate: (items: any[]) => request.post('/site-config/batch', items),
  getRegistrationStatus: () => request.get('/site-config/registration-status'),
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
  getMetrics: (id: number, hours?: number) => request.get(`/hosts/${id}/metrics`, { params: { hours } }),
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
  listSSHLoginLogs: (params?: any) => request.get('/audit/ssh-login-logs', { params }),
  getSSHLoginAnalysis: (params?: any) => request.get('/audit/ssh-login-logs/analysis', { params }),
  collectSSHLoginLogs: (data?: any) => request.post('/audit/ssh-login-logs/collect', data),
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

// ===== Dashboard API =====
export const dashboardApi = {
  getOverview: () => request.get('/dashboard'),
};

// ===== SFTP API =====
export const sftpApi = {
  listFiles: (hostId: number, path: string = '/') =>
    request.get(`/sftp/${hostId}/list`, { params: { path } }),
  mkdir: (hostId: number, path: string, name: string) =>
    request.post(`/sftp/${hostId}/mkdir`, { path, name }),
  renameFile: (hostId: number, path: string, new_name: string) =>
    request.post(`/sftp/${hostId}/rename`, { path, new_name }),
  deleteFile: (hostId: number, path: string) =>
    request.post(`/sftp/${hostId}/delete`, { path }),
  moveFile: (hostId: number, sourcePath: string, targetPath: string) =>
    request.post(`/sftp/${hostId}/move`, { source_path: sourcePath, target_path: targetPath }),
  copyFile: (hostId: number, sourcePath: string, targetPath: string) =>
    request.post(`/sftp/${hostId}/copy`, { source_path: sourcePath, target_path: targetPath }),
  downloadFile: (hostId: number, path: string) =>
    request.get(`/sftp/${hostId}/download`, { params: { path }, responseType: 'arraybuffer' }),
  uploadFile: (hostId: number, path: string, formData: FormData) =>
    request.post(`/sftp/${hostId}/upload`, formData, {
      params: { path },
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  exists: (hostId: number, path: string) =>
    request.get(`/sftp/${hostId}/exists`, { params: { path } }),
};
