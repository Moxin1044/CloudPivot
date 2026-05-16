<template>
  <div class="monitor-page">
    <t-tabs v-model="activeTab">
      <t-tab-panel value="metrics" :label="$t('monitor.title')">
        <div style="display:flex;gap:12px;margin-bottom:12px;align-items:center">
          <t-select v-model="selectedHostId" :options="hostOptions" :placeholder="$t('monitor.selectHost')" style="width:250px" filterable @change="onHostChange" />
          <t-select v-model="timeRange" :options="timeOptions" style="width:120px" @change="loadMetrics" />
          <t-button @click="loadMetrics" :loading="metricsLoading">{{ $t('common.refresh') }}</t-button>
        </div>

        <!-- Dashboard Gauge Row -->
        <t-row :gutter="[12,12]" v-if="latestMetric" style="margin-bottom:12px">
          <t-col :span="4">
            <div class="gauge-card">
              <div ref="cpuGaugeRef" class="gauge-chart"></div>
            </div>
          </t-col>
          <t-col :span="4">
            <div class="gauge-card">
              <div ref="memGaugeRef" class="gauge-chart"></div>
            </div>
          </t-col>
          <t-col :span="4">
            <div class="gauge-card">
              <div ref="diskGaugeRef" class="gauge-chart"></div>
            </div>
          </t-col>
          <t-col :span="6">
            <div class="info-card">
              <div class="info-row"><span class="info-label">{{ $t('monitor.networkIn') }}</span><span class="info-value">{{ latestMetric.network_in_kbps?.toFixed(1) || '-' }} <small>KB/s</small></span></div>
              <div class="info-row"><span class="info-label">{{ $t('monitor.networkOutKbps') }}</span><span class="info-value">{{ latestMetric.network_out_kbps?.toFixed(1) || '-' }} <small>KB/s</small></span></div>
              <div class="info-row"><span class="info-label">{{ $t('monitor.load1') }}</span><span class="info-value">{{ latestMetric.load_1min?.toFixed(2) || '-' }}</span></div>
            </div>
          </t-col>
          <t-col :span="6">
            <div class="info-card">
              <div class="info-row"><span class="info-label">MEM</span><span class="info-value">{{ latestMetric.memory_used_gb?.toFixed(1) || '-' }} / {{ latestMetric.memory_total_gb?.toFixed(1) || '-' }} <small>GB</small></span></div>
              <div class="info-row"><span class="info-label">DISK</span><span class="info-value">{{ latestMetric.disk_used_gb?.toFixed(1) || '-' }} / {{ latestMetric.disk_total_gb?.toFixed(1) || '-' }} <small>GB</small></span></div>
              <div class="info-row"><span class="info-label">Load5/15</span><span class="info-value">{{ latestMetric.load_5min?.toFixed(2) || '-' }} / {{ latestMetric.load_15min?.toFixed(2) || '-' }}</span></div>
            </div>
          </t-col>
        </t-row>

        <!-- Trend Chart -->
        <t-card :bordered="false" style="margin-bottom:12px;padding:0">
          <div ref="chartRef" style="height:280px"></div>
        </t-card>

        <!-- Metrics Table with Pagination -->
        <t-card :bordered="false">
          <t-table
            :data="paginatedMetrics"
            :columns="metricColumns"
            :loading="metricsLoading"
            row-key="id"
            size="small"
            :pagination="pagination"
            @page-change="onPageChange"
          />
        </t-card>
      </t-tab-panel>

      <t-tab-panel value="rules" :label="$t('monitor.alertRules')">
        <t-card :bordered="false">
          <template #actions>
            <t-button theme="primary" @click="showRuleCreate = true">{{ $t('monitor.createRule') }}</t-button>
          </template>
          <t-table :data="rules" :columns="ruleColumns" :loading="rulesLoading" row-key="id" size="small" />
        </t-card>
      </t-tab-panel>
    </t-tabs>

    <t-dialog v-model:visible="showRuleCreate" :header="$t('monitor.createAlertRule')" @confirm="onCreateRule">
      <t-form :data="ruleForm" label-align="top">
        <t-form-item :label="$t('monitor.ruleName')"><t-input v-model="ruleForm.name" /></t-form-item>
        <t-form-item :label="$t('monitor.metricTypeLabel')"><t-select v-model="ruleForm.metric_type" :options="metricTypeOptions" /></t-form-item>
        <t-form-item :label="$t('monitor.conditionLabel')"><t-select v-model="ruleForm.condition" :options="conditionOptions" /></t-form-item>
        <t-form-item :label="$t('monitor.thresholdLabel')"><t-input-number v-model="ruleForm.threshold" /></t-form-item>
        <t-form-item :label="$t('monitor.severityLabel')"><t-select v-model="ruleForm.severity" :options="severityOptions" /></t-form-item>
      </t-form>
    </t-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue';
import { useI18n } from 'vue-i18n';
import { MessagePlugin } from 'tdesign-vue-next';
import { hostApi, monitorApi } from '@/api';
import * as echarts from 'echarts';

const { t } = useI18n();
const activeTab = ref('metrics');
const selectedHostId = ref<number | undefined>(undefined);
const hostOptions = ref<any[]>([]);
const timeRange = ref(1);
const timeOptions = [
  { label: t('monitor.hours1'), value: 1 }, { label: t('monitor.hours6'), value: 6 },
  { label: t('monitor.hours24'), value: 24 }, { label: t('monitor.days7'), value: 168 },
];
const metrics = ref<any[]>([]);
const latestMetric = ref<any>(null);
const rules = ref<any[]>([]);
const metricsLoading = ref(false);
const rulesLoading = ref(false);
const showRuleCreate = ref(false);

// Pagination
const pagination = reactive({
  current: 1,
  pageSize: 15,
  total: 0,
});
const paginatedMetrics = computed(() => {
  const start = (pagination.current - 1) * pagination.pageSize;
  return metrics.value.slice(start, start + pagination.pageSize);
});

function onPageChange({ current, pageSize }: any) {
  pagination.current = current;
  pagination.pageSize = pageSize;
}

// Chart refs
const chartRef = ref<HTMLElement>();
const cpuGaugeRef = ref<HTMLElement>();
const memGaugeRef = ref<HTMLElement>();
const diskGaugeRef = ref<HTMLElement>();
let trendChart: echarts.ECharts | null = null;
let cpuGauge: echarts.ECharts | null = null;
let memGauge: echarts.ECharts | null = null;
let diskGauge: echarts.ECharts | null = null;

const ruleForm = reactive({
  name: '', metric_type: 'cpu_percent', condition: 'gt', threshold: 90, severity: 'warning',
});

const metricTypeOptions = [
  { label: t('monitor.metricTypeCpu'), value: 'cpu_percent' },
  { label: t('monitor.metricTypeMemory'), value: 'memory_percent' },
  { label: t('monitor.metricTypeDisk'), value: 'disk_percent' },
  { label: t('monitor.metricTypeNetIn'), value: 'network_in_kbps' },
  { label: t('monitor.metricTypeNetOut'), value: 'network_out_kbps' },
  { label: t('monitor.metricTypeLoad'), value: 'load_1min' },
];
const conditionOptions = [
  { label: t('monitor.gt'), value: 'gt' }, { label: t('monitor.lt'), value: 'lt' },
  { label: t('monitor.gte'), value: 'gte' }, { label: t('monitor.lte'), value: 'lte' },
];
const severityOptions = [
  { label: t('monitor.info'), value: 'info' }, { label: t('monitor.warning'), value: 'warning' }, { label: t('monitor.critical'), value: 'critical' },
];

const metricColumns = [
  { colKey: 'collected_at', title: t('monitor.collectedAt'), width: 170 },
  { colKey: 'cpu_percent', title: t('monitor.cpuPercent'), width: 80 },
  { colKey: 'memory_percent', title: t('monitor.memoryPercent'), width: 80 },
  { colKey: 'disk_percent', title: t('monitor.diskPercent'), width: 80 },
  { colKey: 'network_in_kbps', title: t('monitor.networkInKbps'), width: 100 },
  { colKey: 'network_out_kbps', title: t('monitor.networkOutKbps'), width: 100 },
  { colKey: 'load_1min', title: t('monitor.load1'), width: 80 },
];

const ruleColumns = [
  { colKey: 'name', title: t('monitor.ruleName') },
  { colKey: 'metric_type', title: t('monitor.metricTypeLabel') },
  { colKey: 'condition', title: t('monitor.conditionLabel') },
  { colKey: 'threshold', title: t('monitor.thresholdLabel') },
  { colKey: 'severity', title: t('monitor.severityLabel') },
  { colKey: 'is_enabled', title: t('common.enabled') },
  { colKey: 'actions', title: t('common.actions'), width: 100,
    cell: (_h: any, { row }: any) => _h('t-button', { variant: 'text', theme: 'danger', size: 'small', onClick: () => onDeleteRule(row.id) }, t('common.delete'))
  },
];

async function loadHosts() {
  try {
    const res: any = await hostApi.list({ limit: 100 });
    const items = Array.isArray(res) ? res : (res.items || []);
    hostOptions.value = items.map((h: any) => ({ label: `${h.name} (${h.ip_address})`, value: h.id }));
    if (hostOptions.value.length) {
      selectedHostId.value = hostOptions.value[0].value;
      await loadMetrics();
    }
  } catch (e) { /* */ }
}

function onHostChange() {
  pagination.current = 1;
  loadMetrics();
}

function formatTime(iso: string) {
  const d = new Date(iso);
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
}

function getGaugeColor(value: number): string {
  if (value >= 90) return '#e34d59';
  if (value >= 70) return '#ed7b2f';
  if (value >= 50) return '#dcc019';
  return '#2ba471';
}

function updateGauge(chart: echarts.ECharts | null, value: number, title: string) {
  if (!chart) return;
  const safeVal = value ?? 0;
  chart.setOption({
    series: [{
      data: [{ value: safeVal, name: title }],
      itemStyle: { color: getGaugeColor(safeVal) },
    }],
  });
}

function initGauges() {
  if (cpuGaugeRef.value) {
    cpuGauge = echarts.init(cpuGaugeRef.value);
    cpuGauge.setOption(makeGaugeOption(t('monitor.cpuLabel')));
  }
  if (memGaugeRef.value) {
    memGauge = echarts.init(memGaugeRef.value);
    memGauge.setOption(makeGaugeOption(t('monitor.memoryLabel')));
  }
  if (diskGaugeRef.value) {
    diskGauge = echarts.init(diskGaugeRef.value);
    diskGauge.setOption(makeGaugeOption(t('monitor.diskLabel')));
  }
}

function makeGaugeOption(title: string) {
  return {
    series: [{
      type: 'gauge',
      startAngle: 210,
      endAngle: -30,
      min: 0,
      max: 100,
      splitNumber: 5,
      progress: { show: true, width: 14, roundCap: true },
      axisLine: { lineStyle: { width: 14, color: [[1, '#e7e7e7']] } },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { distance: 18, fontSize: 10, color: '#999' },
      pointer: { show: false },
      title: { offsetCenter: [0, '70%'], fontSize: 13, color: '#666' },
      detail: {
        valueAnimation: true, fontSize: 22, fontWeight: 700,
        offsetCenter: [0, '30%'], formatter: '{value}%',
        color: 'inherit',
      },
      data: [{ value: 0, name: title }],
    }],
  };
}

function updateTrendChart(data: any[]) {
  if (!trendChart) return;
  const times = data.map((d) => formatTime(d.collected_at));
  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: [t('monitor.cpuPercent'), t('monitor.memoryPercent'), t('monitor.diskPercent')], bottom: 0, textStyle: { fontSize: 11 } },
    grid: { left: '3%', right: '4%', bottom: '14%', top: '8%', containLabel: true },
    xAxis: { type: 'category', boundaryGap: false, data: times, axisLabel: { fontSize: 10 } },
    yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%', fontSize: 10 } },
    series: [
      { name: t('monitor.cpuPercent'), type: 'line', smooth: true, symbol: 'none', data: data.map((d) => d.cpu_percent ?? null) },
      { name: t('monitor.memoryPercent'), type: 'line', smooth: true, symbol: 'none', data: data.map((d) => d.memory_percent ?? null) },
      { name: t('monitor.diskPercent'), type: 'line', smooth: true, symbol: 'none', data: data.map((d) => d.disk_percent ?? null) },
    ],
  }, true);
}

async function loadMetrics() {
  if (!selectedHostId.value) return;
  metricsLoading.value = true;
  try {
    const res: any = await monitorApi.getMetrics(selectedHostId.value, timeRange.value);
    metrics.value = Array.isArray(res) ? res : (res.items || []);
    pagination.total = metrics.value.length;

    const latest: any = await monitorApi.getLatestMetric(selectedHostId.value);
    latestMetric.value = latest;

    if (metrics.value.length > 0) {
      updateTrendChart(metrics.value);
    }

    // Update gauges
    await nextTick();
    if (!cpuGauge) initGauges();
    updateGauge(cpuGauge, latest?.cpu_percent, t('monitor.cpuLabel'));
    updateGauge(memGauge, latest?.memory_percent, t('monitor.memoryLabel'));
    updateGauge(diskGauge, latest?.disk_percent, t('monitor.diskLabel'));
  } finally { metricsLoading.value = false; }
}

async function loadRules() {
  rulesLoading.value = true;
  try { rules.value = await monitorApi.listAlertRules(); } finally { rulesLoading.value = false; }
}

async function onCreateRule() {
  await monitorApi.createAlertRule(ruleForm);
  MessagePlugin.success(t('monitor.ruleCreated'));
  showRuleCreate.value = false;
  loadRules();
}

async function onDeleteRule(id: number) {
  await monitorApi.deleteAlertRule(id);
  loadRules();
}

function onResize() {
  trendChart?.resize();
  cpuGauge?.resize();
  memGauge?.resize();
  diskGauge?.resize();
}

onMounted(() => {
  loadHosts();
  loadRules();
  if (chartRef.value) {
    trendChart = echarts.init(chartRef.value);
  }
  window.addEventListener('resize', onResize);
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize);
  trendChart?.dispose();
  cpuGauge?.dispose();
  memGauge?.dispose();
  diskGauge?.dispose();
});
</script>

<style scoped>
.gauge-card {
  background: var(--td-bg-color-container);
  border-radius: 8px;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.gauge-chart {
  width: 100%;
  height: 160px;
}
.info-card {
  background: var(--td-bg-color-container);
  border-radius: 8px;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 12px;
  height: 168px;
}
.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.info-label {
  color: var(--td-text-color-secondary);
  font-size: 13px;
}
.info-value {
  font-size: 15px;
  font-weight: 600;
  color: var(--td-text-color-primary);
}
.info-value small {
  font-weight: 400;
  font-size: 11px;
  color: var(--td-text-color-secondary);
}
</style>
