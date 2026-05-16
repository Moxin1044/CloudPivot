<template>
  <div class="monitor-page">
    <t-tabs v-model="activeTab">
      <t-tab-panel value="metrics" :label="$t('monitor.title')">
        <t-card :bordered="false">
          <div style="display:flex;gap:16px;margin-bottom:16px">
            <t-select v-model="selectedHostId" :options="hostOptions" :placeholder="$t('monitor.selectHost')" style="width:250px" filterable />
            <t-select v-model="timeRange" :options="timeOptions" style="width:120px" />
            <t-button @click="loadMetrics" :loading="metricsLoading">{{ $t('common.refresh') }}</t-button>
          </div>
          <div v-if="latestMetric" style="margin-bottom:16px">
            <t-row :gutter="[16,16]">
              <t-col :span="3">
                <t-card :bordered="false" class="metric-card">
                  <div class="metric-label">{{ $t('monitor.cpuLabel') }}</div>
                  <div class="metric-value">{{ latestMetric.cpu_percent?.toFixed(1) || '-' }}%</div>
                </t-card>
              </t-col>
              <t-col :span="3">
                <t-card :bordered="false" class="metric-card">
                  <div class="metric-label">{{ $t('monitor.memoryLabel') }}</div>
                  <div class="metric-value">{{ latestMetric.memory_percent?.toFixed(1) || '-' }}%</div>
                </t-card>
              </t-col>
              <t-col :span="3">
                <t-card :bordered="false" class="metric-card">
                  <div class="metric-label">{{ $t('monitor.diskLabel') }}</div>
                  <div class="metric-value">{{ latestMetric.disk_percent?.toFixed(1) || '-' }}%</div>
                </t-card>
              </t-col>
              <t-col :span="3">
                <t-card :bordered="false" class="metric-card">
                  <div class="metric-label">{{ $t('monitor.networkIn') }}</div>
                  <div class="metric-value">{{ latestMetric.network_in_mbps?.toFixed(1) || '-' }} Mbps</div>
                </t-card>
              </t-col>
            </t-row>
          </div>
          <t-table :data="metrics" :columns="metricColumns" :loading="metricsLoading" row-key="id" size="small" />
        </t-card>
      </t-tab-panel>
      <t-tab-panel value="rules" :label="$t('monitor.alertRules')">
        <t-card :bordered="false">
          <template #actions>
            <t-button theme="primary" @click="showRuleCreate = true">{{ $t('monitor.createRule') }}</t-button>
          </template>
          <t-table :data="rules" :columns="ruleColumns" :loading="rulesLoading" row-key="id" />
        </t-card>
      </t-tab-panel>
    </t-tabs>

    <t-dialog v-model:visible="showRuleCreate" :header="$t('monitor.createAlertRule')" @confirm="onCreateRule">
      <t-form :data="ruleForm" label-align="top">
        <t-form-item :label="$t('monitor.ruleName')"><t-input v-model="ruleForm.name" /></t-form-item>
        <t-form-item :label="$t('monitor.metricTypeLabel')"><t-input v-model="ruleForm.metric_type" placeholder="cpu_percent, memory_percent..." /></t-form-item>
        <t-form-item :label="$t('monitor.conditionLabel')"><t-select v-model="ruleForm.condition" :options="conditionOptions" /></t-form-item>
        <t-form-item :label="$t('monitor.thresholdLabel')"><t-input-number v-model="ruleForm.threshold" /></t-form-item>
        <t-form-item :label="$t('monitor.severityLabel')"><t-select v-model="ruleForm.severity" :options="severityOptions" /></t-form-item>
      </t-form>
    </t-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { MessagePlugin } from 'tdesign-vue-next';
import { hostApi, monitorApi } from '@/api';

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

const ruleForm = reactive({
  name: '', metric_type: 'cpu_percent', condition: 'gt', threshold: 90, severity: 'warning',
});

const conditionOptions = [
  { label: t('monitor.gt'), value: 'gt' }, { label: t('monitor.lt'), value: 'lt' },
  { label: t('monitor.gte'), value: 'gte' }, { label: t('monitor.lte'), value: 'lte' },
];
const severityOptions = [
  { label: t('monitor.info'), value: 'info' }, { label: t('monitor.warning'), value: 'warning' }, { label: t('monitor.critical'), value: 'critical' },
];

const metricColumns = [
  { colKey: 'collected_at', title: t('monitor.collectedAt'), width: 180 },
  { colKey: 'cpu_percent', title: t('monitor.cpuPercent'), width: 80 },
  { colKey: 'memory_percent', title: t('monitor.memoryPercent'), width: 80 },
  { colKey: 'disk_percent', title: t('monitor.diskPercent'), width: 80 },
  { colKey: 'network_in_mbps', title: t('monitor.networkInMbps'), width: 100 },
  { colKey: 'network_out_mbps', title: t('monitor.networkOutMbps'), width: 100 },
  { colKey: 'load_1min', title: t('monitor.load1'), width: 80 },
];

const ruleColumns = [
  { colKey: 'name', title: t('monitor.ruleName') },
  { colKey: 'metric_type', title: t('monitor.metricTypeLabel') },
  { colKey: 'condition', title: t('monitor.conditionLabel') },
  { colKey: 'threshold', title: t('monitor.thresholdLabel') },
  { colKey: 'severity', title: t('monitor.severityLabel') },
  { colKey: 'is_enabled', title: t('common.enabled') },
  { colKey: 'actions', title: t('common.actions'),
    cell: (_h: any, { row }: any) => _h('t-button', { props: { variant: 'text', theme: 'danger', size: 'small' }, on: { click: () => onDeleteRule(row.id) } }, t('common.delete'))
  },
];

async function loadHosts() {
  try {
    const res: any = await hostApi.list({ limit: 100 });
    hostOptions.value = (Array.isArray(res) ? res : []).map((h: any) => ({ label: `${h.name} (${h.ip_address})`, value: h.id }));
    if (hostOptions.value.length) selectedHostId.value = hostOptions.value[0].value;
  } catch (e) { /* */ }
}

async function loadMetrics() {
  if (!selectedHostId.value) return;
  metricsLoading.value = true;
  try {
    metrics.value = await monitorApi.getMetrics(selectedHostId.value, timeRange.value);
    const latest: any = await monitorApi.getLatestMetric(selectedHostId.value);
    latestMetric.value = latest;
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

onMounted(() => { loadHosts(); loadRules(); });
</script>

<style scoped>
.metric-card { text-align: center; }
.metric-label { color: var(--td-text-color-secondary); font-size: 13px; }
.metric-value { font-size: 24px; font-weight: 700; margin-top: 4px; }
</style>
