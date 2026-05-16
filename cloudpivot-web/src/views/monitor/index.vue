<template>
  <div class="monitor-page">
    <t-tabs v-model="activeTab">
      <t-tab-panel value="metrics" :label="$t('monitor.title')">
        <t-card :bordered="false">
          <div style="display:flex;gap:16px;margin-bottom:16px">
            <t-select v-model="selectedHostId" :options="hostOptions" placeholder="选择主机" style="width:250px" filterable />
            <t-select v-model="timeRange" :options="timeOptions" style="width:120px" />
            <t-button @click="loadMetrics" :loading="metricsLoading">刷新</t-button>
          </div>
          <div v-if="latestMetric" style="margin-bottom:16px">
            <t-row :gutter="[16,16]">
              <t-col :span="3">
                <t-card :bordered="false" class="metric-card">
                  <div class="metric-label">CPU</div>
                  <div class="metric-value">{{ latestMetric.cpu_percent?.toFixed(1) || '-' }}%</div>
                </t-card>
              </t-col>
              <t-col :span="3">
                <t-card :bordered="false" class="metric-card">
                  <div class="metric-label">内存</div>
                  <div class="metric-value">{{ latestMetric.memory_percent?.toFixed(1) || '-' }}%</div>
                </t-card>
              </t-col>
              <t-col :span="3">
                <t-card :bordered="false" class="metric-card">
                  <div class="metric-label">磁盘</div>
                  <div class="metric-value">{{ latestMetric.disk_percent?.toFixed(1) || '-' }}%</div>
                </t-card>
              </t-col>
              <t-col :span="3">
                <t-card :bordered="false" class="metric-card">
                  <div class="metric-label">网络入</div>
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

    <t-dialog v-model:visible="showRuleCreate" header="创建告警规则" @confirm="onCreateRule">
      <t-form :data="ruleForm" label-align="top">
        <t-form-item label="名称"><t-input v-model="ruleForm.name" /></t-form-item>
        <t-form-item label="指标类型"><t-input v-model="ruleForm.metric_type" placeholder="cpu_percent, memory_percent..." /></t-form-item>
        <t-form-item label="条件"><t-select v-model="ruleForm.condition" :options="conditionOptions" /></t-form-item>
        <t-form-item label="阈值"><t-input-number v-model="ruleForm.threshold" /></t-form-item>
        <t-form-item label="严重程度"><t-select v-model="ruleForm.severity" :options="severityOptions" /></t-form-item>
      </t-form>
    </t-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { MessagePlugin } from 'tdesign-vue-next';
import { hostApi, monitorApi } from '@/api';

const activeTab = ref('metrics');
const selectedHostId = ref<number | undefined>(undefined);
const hostOptions = ref<any[]>([]);
const timeRange = ref(1);
const timeOptions = [
  { label: '1小时', value: 1 }, { label: '6小时', value: 6 },
  { label: '24小时', value: 24 }, { label: '7天', value: 168 },
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
  { label: '大于', value: 'gt' }, { label: '小于', value: 'lt' },
  { label: '大于等于', value: 'gte' }, { label: '小于等于', value: 'lte' },
];
const severityOptions = [
  { label: '信息', value: 'info' }, { label: '警告', value: 'warning' }, { label: '严重', value: 'critical' },
];

const metricColumns = [
  { colKey: 'collected_at', title: '时间', width: 180 },
  { colKey: 'cpu_percent', title: 'CPU%', width: 80 },
  { colKey: 'memory_percent', title: '内存%', width: 80 },
  { colKey: 'disk_percent', title: '磁盘%', width: 80 },
  { colKey: 'network_in_mbps', title: '网络入(Mbps)', width: 100 },
  { colKey: 'network_out_mbps', title: '网络出(Mbps)', width: 100 },
  { colKey: 'load_1min', title: 'Load1', width: 80 },
];

const ruleColumns = [
  { colKey: 'name', title: '名称' },
  { colKey: 'metric_type', title: '指标' },
  { colKey: 'condition', title: '条件' },
  { colKey: 'threshold', title: '阈值' },
  { colKey: 'severity', title: '严重程度' },
  { colKey: 'is_enabled', title: '启用' },
  { colKey: 'actions', title: '操作',
    cell: (_h: any, { row }: any) => _h('t-button', { props: { variant: 'text', theme: 'danger', size: 'small' }, on: { click: () => onDeleteRule(row.id) } }, '删除')
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
  MessagePlugin.success('创建成功');
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
