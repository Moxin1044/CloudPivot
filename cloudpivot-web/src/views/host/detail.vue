<template>
  <div class="host-detail">
    <t-card :bordered="false">
      <template #title>
        <t-button variant="text" @click="$router.back()">
          <template #icon><t-icon name="chevron-left" /></template>
          {{ $t('common.back') }}
        </t-button>
        {{ host.name }}
      </template>
      <t-descriptions :data="descData" :column="2" bordered />
      <div style="margin-top: 16px; display: flex; gap: 8px;">
        <t-button theme="primary" @click="onTest">{{ $t('host.testConnectivity') }}</t-button>
        <t-button variant="outline" @click="$router.push({ path: '/terminal', query: { hostId: host.id } })">
          {{ $t('terminal.connect') }}
        </t-button>
      </div>
    </t-card>

    <t-card :bordered="false" style="margin-top: 16px" :title="$t('host.monitoring')">
      <div style="display: flex; gap: 8px; margin-bottom: 16px;">
        <t-select v-model="timeRange" :options="timeOptions" style="width: 140px" @change="loadMetrics" />
        <t-button variant="outline" @click="loadMetrics">
          <template #icon><t-icon name="refresh" /></template>
        </t-button>
      </div>
      <div ref="cpuChartRef" style="height: 280px; margin-bottom: 16px;"></div>
      <div ref="memChartRef" style="height: 280px; margin-bottom: 16px;"></div>
      <div ref="diskChartRef" style="height: 280px; margin-bottom: 16px;"></div>
      <div ref="netChartRef" style="height: 280px;"></div>
    </t-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue';
import { useRoute } from 'vue-router';
import { MessagePlugin } from 'tdesign-vue-next';
import { useI18n } from 'vue-i18n';
import { hostApi } from '@/api';
import * as echarts from 'echarts';

const route = useRoute();
const { t } = useI18n();
const hostId = Number(route.params.id);
const host = ref<any>({});
const descData = ref<any[]>([]);
const timeRange = ref(6);
const timeOptions = [
  { label: '1h', value: 1 },
  { label: '6h', value: 6 },
  { label: '24h', value: 24 },
  { label: '7d', value: 168 },
];

const cpuChartRef = ref<HTMLElement>();
const memChartRef = ref<HTMLElement>();
const diskChartRef = ref<HTMLElement>();
const netChartRef = ref<HTMLElement>();

let cpuChart: echarts.ECharts | null = null;
let memChart: echarts.ECharts | null = null;
let diskChart: echarts.ECharts | null = null;
let netChart: echarts.ECharts | null = null;

function formatTime(iso: string) {
  const d = new Date(iso);
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
}

function initCharts() {
  if (cpuChartRef.value) cpuChart = echarts.init(cpuChartRef.value);
  if (memChartRef.value) memChart = echarts.init(memChartRef.value);
  if (diskChartRef.value) diskChart = echarts.init(diskChartRef.value);
  if (netChartRef.value) netChart = echarts.init(netChartRef.value);
}

function updateCharts(data: any[]) {
  const times = data.map((d) => formatTime(d.collected_at));

  const commonOption = (title: string, series: any[]) => ({
    title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', boundaryGap: false, data: times },
    yAxis: { type: 'value' },
    series,
  });

  cpuChart?.setOption(
    commonOption(t('monitor.cpuLabel'), [
      {
        name: t('monitor.cpuPercent'),
        type: 'line',
        smooth: true,
        areaStyle: { opacity: 0.2 },
        data: data.map((d) => d.cpu_percent ?? null),
      },
    ]),
    true
  );

  memChart?.setOption(
    commonOption(t('monitor.memoryLabel'), [
      {
        name: t('monitor.memoryPercent'),
        type: 'line',
        smooth: true,
        areaStyle: { opacity: 0.2 },
        data: data.map((d) => d.memory_percent ?? null),
      },
    ]),
    true
  );

  diskChart?.setOption(
    commonOption(t('monitor.diskLabel'), [
      {
        name: t('monitor.diskPercent'),
        type: 'line',
        smooth: true,
        areaStyle: { opacity: 0.2 },
        data: data.map((d) => d.disk_percent ?? null),
      },
    ]),
    true
  );

  netChart?.setOption(
    commonOption(t('monitor.network'), [
      {
        name: t('monitor.networkInMbps'),
        type: 'line',
        smooth: true,
        data: data.map((d) => d.network_in_mbps ?? null),
      },
      {
        name: t('monitor.networkOutMbps'),
        type: 'line',
        smooth: true,
        data: data.map((d) => d.network_out_mbps ?? null),
      },
    ]),
    true
  );
}

async function loadHost() {
  try {
    const res: any = await hostApi.get(hostId);
    host.value = res;
    descData.value = [
      { label: t('common.name'), value: res.name },
      { label: t('host.hostname'), value: res.hostname },
      { label: t('host.ip'), value: res.ip_address },
      { label: t('host.publicIp'), value: res.public_ip || '-' },
      { label: t('host.port'), value: res.port },
      { label: t('host.username'), value: res.username },
      { label: t('host.authType'), value: res.auth_type },
      { label: t('common.status'), value: res.status },
      { label: t('host.osName'), value: res.os_name || '-' },
      { label: t('host.osVersion'), value: res.os_version || '-' },
      { label: t('host.lastConnected'), value: res.last_connected_at || '-' },
    ];
  } catch (e) { /* handled */ }
}

async function loadMetrics() {
  try {
    const res: any = await hostApi.getMetrics(hostId, timeRange.value);
    if (Array.isArray(res) && res.length > 0) {
      updateCharts(res);
    }
  } catch (e) { /* handled */ }
}

async function onTest() {
  try {
    const res: any = await hostApi.testConnectivity(hostId);
    if (res.success) MessagePlugin.success(`${t('host.connectSuccess')} (${res.latency_ms?.toFixed(0)}ms)`);
    else MessagePlugin.error(`${t('host.connectFailed')}: ${res.message}`);
    loadHost();
  } catch (e) { /* handled */ }
}

function onResize() {
  cpuChart?.resize();
  memChart?.resize();
  diskChart?.resize();
  netChart?.resize();
}

onMounted(() => {
  loadHost();
  initCharts();
  loadMetrics();
  window.addEventListener('resize', onResize);
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize);
  cpuChart?.dispose();
  memChart?.dispose();
  diskChart?.dispose();
  netChart?.dispose();
});
</script>
