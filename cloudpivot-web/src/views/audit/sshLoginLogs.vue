<template>
  <div class="ssh-login-logs-page">
    <t-card :bordered="false">
      <template #actions>
        <t-space>
          <t-input v-model="filter.keyword" placeholder="搜索用户 / IP / 主机" clearable style="width: 220px" @enter="onRefresh" @clear="onRefresh" />
          <t-select v-model="filter.hours" :options="hourOptions" style="width: 120px" @change="onRefresh" />
          <t-select v-if="hostOptions.length" v-model="filter.host_id" :options="hostOptions" clearable style="width: 180px" placeholder="选择主机" @change="onRefresh" />
          <t-button variant="outline" @click="onRefresh">{{ $t('common.refresh') }}</t-button>
          <t-button v-if="isAdmin" theme="primary" @click="onCollect">采集日志</t-button>
        </t-space>
      </template>

      <!-- 统计卡片 -->
      <t-row :gutter="[16, 16]" style="margin-bottom: 16px">
        <t-col :span="2">
          <t-statistic title="总登录次数" :value="summary.total_logins" unit="次" />
        </t-col>
        <t-col :span="2">
          <t-statistic title="失败登录" :value="summary.failed_logins" unit="次" theme="error" />
        </t-col>
        <t-col :span="2">
          <t-statistic title="独立IP数" :value="summary.unique_ips" unit="个" />
        </t-col>
        <t-col :span="2">
          <t-statistic title="暴力破解" :value="summary.brute_force_attempts" unit="次" theme="warning" />
        </t-col>
        <t-col :span="2">
          <t-statistic title="新IP登录" :value="summary.new_ip_logins" unit="次" theme="primary" />
        </t-col>
        <t-col :span="2">
          <t-statistic title="独立用户" :value="summary.unique_users" unit="个" />
        </t-col>
      </t-row>

      <!-- 图表 -->
      <t-row :gutter="[16, 16]" style="margin-bottom: 16px">
        <t-col :span="12">
          <div ref="trendChartRef" style="width: 100%; height: 260px" />
        </t-col>
      </t-row>
      <t-row :gutter="[16, 16]" style="margin-bottom: 16px">
        <t-col :span="6">
          <div ref="riskChartRef" style="width: 100%; height: 220px" />
        </t-col>
        <t-col :span="6">
          <div ref="ipChartRef" style="width: 100%; height: 220px" />
        </t-col>
      </t-row>

      <!-- 日志表格 -->
      <t-table
        :data="logs"
        :columns="columns"
        :loading="loading"
        row-key="id"
        :pagination="pagination"
        @page-change="onPageChange"
      />
    </t-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { MessagePlugin } from 'tdesign-vue-next';
import * as echarts from 'echarts';
import { auditApi, hostApi } from '@/api';
import { useUserStore } from '@/stores/app';

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
const filter = ref({ hours: 24, host_id: undefined as number | undefined, keyword: '' });
const hostOptions = ref<any[]>([]);

const pagination = ref({ current: 1, pageSize: 20, total: 0 });

const hourOptions = [
  { label: '最近1小时', value: 1 },
  { label: '最近6小时', value: 6 },
  { label: '最近24小时', value: 24 },
  { label: '最近7天', value: 168 },
];

const columns = [
  { colKey: 'host_name', title: '主机', width: 140 },
  { colKey: 'username', title: t('audit.username'), width: 100 },
  { colKey: 'login_ip', title: t('audit.loginIp'), width: 140 },
  { colKey: 'login_port', title: '端口', width: 80 },
  { colKey: 'auth_method', title: '认证方式', width: 100 },
  { colKey: 'is_success', title: t('audit.success'), width: 80,
    cell: (h: any, { row }: any) => h('t-tag', { theme: row.is_success ? 'success' : 'danger', size: 'small' }, row.is_success ? '成功' : '失败'),
  },
  { colKey: 'risk_level', title: t('audit.riskLevel'), width: 90,
    cell: (h: any, { row }: any) => {
      const theme = row.risk_level === 'danger' ? 'danger' : row.risk_level === 'warning' ? 'warning' : 'default';
      const label = row.risk_level === 'danger' ? '危险' : row.risk_level === 'warning' ? '警告' : '安全';
      return h('t-tag', { theme, size: 'small' }, label);
    },
  },
  { colKey: 'is_brute_force', title: '暴力破解', width: 90,
    cell: (h: any, { row }: any) => row.is_brute_force ? h('t-tag', { theme: 'danger', size: 'small' }, '是') : h('span', '-'),
  },
  { colKey: 'is_new_ip', title: '新IP', width: 80,
    cell: (h: any, { row }: any) => row.is_new_ip ? h('t-tag', { theme: 'warning', size: 'small' }, '是') : h('span', '-'),
  },
  { colKey: 'login_at', title: t('audit.loginAt'), width: 180 },
  { colKey: 'duration_seconds', title: '时长(s)', width: 90 },
];

let trendChart: echarts.ECharts | null = null;
let riskChart: echarts.ECharts | null = null;
let ipChart: echarts.ECharts | null = null;
const trendChartRef = ref<HTMLDivElement | null>(null);
const riskChartRef = ref<HTMLDivElement | null>(null);
const ipChartRef = ref<HTMLDivElement | null>(null);

async function loadHosts() {
  try {
    const res: any = await hostApi.list();
    hostOptions.value = (res.data || res || []).map((h: any) => ({ label: h.name, value: h.id }));
  } catch (e) { /* ignore */ }
}

async function loadData() {
  loading.value = true;
  try {
    const params = {
      hours: filter.value.hours,
      host_id: filter.value.host_id,
      keyword: filter.value.keyword || undefined,
      skip: (pagination.value.current - 1) * pagination.value.pageSize,
      limit: pagination.value.pageSize,
    };
    const [logsRes, analysisRes]: any = await Promise.all([
      auditApi.listSSHLoginLogs(params),
      auditApi.getSSHLoginAnalysis({ hours: filter.value.hours, host_id: filter.value.host_id }),
    ]);
    logs.value = logsRes.data || logsRes || [];
    summary.value = analysisRes.data || analysisRes || summary.value;
    pagination.value.total = summary.value.total_logins || 0;
    nextTick(() => renderCharts());
  } catch (e) {
    MessagePlugin.error('加载SSH登录日志失败');
  } finally {
    loading.value = false;
  }
}

function renderCharts() {
  if (trendChartRef.value) {
    if (!trendChart) trendChart = echarts.init(trendChartRef.value);
    const data = summary.value.hourly_trend || [];
    trendChart.setOption({
      title: { text: '登录趋势', left: 'center', textStyle: { fontSize: 14 } },
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: data.map((d: any) => d.hour), axisLabel: { rotate: 30 } },
      yAxis: { type: 'value', minInterval: 1 },
      series: [
        { name: '登录次数', type: 'line', smooth: true, data: data.map((d: any) => d.count), areaStyle: {} },
      ],
      grid: { left: 50, right: 20, top: 40, bottom: 50 },
    });
  }
  if (riskChartRef.value) {
    if (!riskChart) riskChart = echarts.init(riskChartRef.value);
    const data = summary.value.risk_distribution || [];
    riskChart.setOption({
      title: { text: '风险分布', left: 'center', textStyle: { fontSize: 14 } },
      tooltip: { trigger: 'item' },
      series: [
        {
          type: 'pie',
          radius: ['40%', '70%'],
          data: data.map((d: any) => ({ name: d.level, value: d.count })),
          label: { formatter: '{b}: {c}' },
        },
      ],
    });
  }
  if (ipChartRef.value) {
    if (!ipChart) ipChart = echarts.init(ipChartRef.value);
    const data = summary.value.top_source_ips || [];
    ipChart.setOption({
      title: { text: 'TOP10 来源IP', left: 'center', textStyle: { fontSize: 14 } },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      xAxis: { type: 'value' },
      yAxis: { type: 'category', data: data.map((d: any) => d.ip).reverse() },
      series: [{ type: 'bar', data: data.map((d: any) => d.count).reverse() }],
      grid: { left: 120, right: 20, top: 30, bottom: 20 },
    });
  }
}

function onPageChange(pageInfo: any) {
  pagination.value.current = pageInfo.current;
  pagination.value.pageSize = pageInfo.pageSize;
  loadData();
}

function onRefresh() {
  pagination.value.current = 1;
  loadData();
}

async function onCollect() {
  try {
    const res: any = await auditApi.collectSSHLoginLogs({ host_id: filter.value.host_id });
    MessagePlugin.success(res.message || '采集完成');
    loadData();
  } catch (e) {
    MessagePlugin.error('采集失败');
  }
}

function onResize() {
  trendChart?.resize();
  riskChart?.resize();
  ipChart?.resize();
}

onMounted(() => {
  loadHosts();
  loadData();
  window.addEventListener('resize', onResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', onResize);
  trendChart?.dispose();
  riskChart?.dispose();
  ipChart?.dispose();
});
</script>

<style scoped>
.ssh-login-logs-page {
  padding: 16px;
}
</style>
