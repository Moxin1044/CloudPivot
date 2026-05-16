<template>
  <div class="ssh-login-logs-page">
    <t-card :bordered="false">
      <template #actions>
        <t-space>
          <t-input v-model="filter.keyword" placeholder="搜索用户 / IP / 主机" clearable style="width: 220px" @enter="onRefresh" @clear="onRefresh" />
          <t-select v-model="filter.hours" :options="hourOptions" style="width: 120px" @change="onRefresh" />
          <t-button variant="outline" @click="onRefresh">{{ $t('common.refresh') }}</t-button>
          <t-button v-if="isAdmin" theme="primary" @click="onCollect">采集日志</t-button>
        </t-space>
      </template>

      <!-- 按主机分Tab展示 -->
      <t-tabs v-model="activeHostTab" @change="onHostTabChange">
        <t-tab-panel value="all" label="全部主机">
          <ssh-host-panel
            :logs="logs"
            :summary="summary"
            :loading="loading"
            :pagination="pagination"
            @page-change="onPageChange"
          />
        </t-tab-panel>
        <t-tab-panel
          v-for="h in hostOptions"
          :key="h.value"
          :value="String(h.value)"
          :label="h.label"
        >
          <ssh-host-panel
            :logs="hostLogsMap[h.value] || []"
            :summary="hostSummaryMap[h.value] || emptySummary"
            :loading="hostLoading[h.value] || false"
            :pagination="hostPaginationMap[h.value] || defaultPagination"
            @page-change="(p: any) => onHostPageChange(h.value, p)"
          />
        </t-tab-panel>
      </t-tabs>
    </t-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, reactive } from 'vue';
import { useI18n } from 'vue-i18n';
import { MessagePlugin } from 'tdesign-vue-next';
import { auditApi, hostApi } from '@/api';
import { useUserStore } from '@/stores/app';
import SshHostPanel from './sshHostPanel.vue';

const { t } = useI18n();
const userStore = useUserStore();
const isAdmin = computed(() => userStore.userInfo?.role === 'admin');

const loading = ref(false);
const logs = ref<any[]>([]);
const summary = ref<any>({
  total_logins: 0,
  failed_logins: 0,
  unique_ips: 0,
  unique_users: 0,
  brute_force_attempts: 0,
  new_ip_logins: 0,
  top_source_ips: [],
  top_users: [],
  hourly_trend: [],
  risk_distribution: [],
});
const filter = ref({ hours: 24, keyword: '' });
const hostOptions = ref<any[]>([]);

const pagination = ref({ current: 1, pageSize: 20, total: 0 });
const activeHostTab = ref('all');

const emptySummary = {
  total_logins: 0,
  failed_logins: 0,
  unique_ips: 0,
  unique_users: 0,
  brute_force_attempts: 0,
  new_ip_logins: 0,
  top_source_ips: [],
  top_users: [],
  hourly_trend: [],
  risk_distribution: [],
};
const defaultPagination = { current: 1, pageSize: 20, total: 0 };

const hostLogsMap = reactive<Record<number, any[]>>({});
const hostSummaryMap = reactive<Record<number, any>>({});
const hostLoading = reactive<Record<number, boolean>>({});
const hostPaginationMap = reactive<Record<number, { current: number; pageSize: number; total: number }>>({});

const hourOptions = [
  { label: '最近1小时', value: 1 },
  { label: '最近6小时', value: 6 },
  { label: '最近24小时', value: 24 },
  { label: '最近7天', value: 168 },
];

async function loadHosts() {
  try {
    const res: any = await hostApi.list({ limit: 1000 });
    const items = Array.isArray(res) ? res : (res.items || []);
    hostOptions.value = items.map((h: any) => ({ label: `${h.name} (${h.ip_address})`, value: h.id }));
  } catch (e) { /* ignore */ }
}

async function loadData() {
  loading.value = true;
  try {
    const params = {
      hours: filter.value.hours,
      keyword: filter.value.keyword || undefined,
      skip: (pagination.value.current - 1) * pagination.value.pageSize,
      limit: pagination.value.pageSize,
    };
    const [logsRes, analysisRes]: any = await Promise.all([
      auditApi.listSSHLoginLogs(params),
      auditApi.getSSHLoginAnalysis({ hours: filter.value.hours }),
    ]);
    const logsData = logsRes.items || logsRes.data || [];
    const total = logsRes.total ?? 0;
    logs.value = logsData;
    summary.value = analysisRes.data || analysisRes || summary.value;
    pagination.value.total = total;
  } catch (e) {
    MessagePlugin.error('加载SSH登录日志失败');
  } finally {
    loading.value = false;
  }
}

async function loadHostData(hostId: number, page = 1, pageSize = 20) {
  if (hostLoading[hostId]) return;
  hostLoading[hostId] = true;
  try {
    const params = {
      hours: filter.value.hours,
      host_id: hostId,
      keyword: filter.value.keyword || undefined,
      skip: (page - 1) * pageSize,
      limit: pageSize,
    };
    const [logsRes, analysisRes]: any = await Promise.all([
      auditApi.listSSHLoginLogs(params),
      auditApi.getSSHLoginAnalysis({ hours: filter.value.hours, host_id: hostId }),
    ]);
    const logsData = logsRes.items || logsRes.data || [];
    const total = logsRes.total ?? 0;
    hostLogsMap[hostId] = logsData;
    hostSummaryMap[hostId] = analysisRes.data || analysisRes || emptySummary;
    if (!hostPaginationMap[hostId]) {
      hostPaginationMap[hostId] = { current: 1, pageSize: 20, total: 0 };
    }
    hostPaginationMap[hostId].current = page;
    hostPaginationMap[hostId].pageSize = pageSize;
    hostPaginationMap[hostId].total = total;
  } catch (e) {
    MessagePlugin.error(`加载主机 ${hostId} 日志失败`);
  } finally {
    hostLoading[hostId] = false;
  }
}

function onPageChange(pageInfo: any) {
  pagination.value.current = pageInfo.current;
  pagination.value.pageSize = pageInfo.pageSize;
  loadData();
}

function onHostPageChange(hostId: number, pageInfo: any) {
  if (!hostPaginationMap[hostId]) {
    hostPaginationMap[hostId] = { current: 1, pageSize: 20, total: 0 };
  }
  hostPaginationMap[hostId].current = pageInfo.current;
  hostPaginationMap[hostId].pageSize = pageInfo.pageSize;
  loadHostData(hostId, pageInfo.current, pageInfo.pageSize);
}

function onHostTabChange(value: string | number) {
  if (value === 'all') {
    loadData();
    return;
  }
  const hostId = Number(value);
  if (!hostLogsMap[hostId]) {
    loadHostData(hostId, 1, 20);
  }
}

function onRefresh() {
  pagination.value.current = 1;
  // Reset host data
  Object.keys(hostLogsMap).forEach((k) => delete hostLogsMap[Number(k)]);
  Object.keys(hostSummaryMap).forEach((k) => delete hostSummaryMap[Number(k)]);
  Object.keys(hostPaginationMap).forEach((k) => delete hostPaginationMap[Number(k)]);
  if (activeHostTab.value === 'all') {
    loadData();
  } else {
    loadHostData(Number(activeHostTab.value), 1, 20);
  }
}

async function onCollect() {
  try {
    const hostId = activeHostTab.value === 'all' ? undefined : Number(activeHostTab.value);
    const res: any = await auditApi.collectSSHLoginLogs({ host_id: hostId });
    MessagePlugin.success(res.message || '采集完成');
    onRefresh();
  } catch (e) {
    MessagePlugin.error('采集失败');
  }
}

onMounted(() => {
  loadHosts();
  loadData();
});
</script>

<style scoped>
.ssh-login-logs-page {
  padding: 16px;
}
</style>
