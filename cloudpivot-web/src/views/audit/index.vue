<template>
  <div class="audit-page">
    <t-tabs v-model="activeTab">
      <t-tab-panel value="sessions" :label="$t('audit.sessions')">
        <t-card :bordered="false">
          <t-table :data="sessions" :columns="sessionColumns" :loading="loading" row-key="id" />
        </t-card>
      </t-tab-panel>
      <t-tab-panel value="commands" :label="$t('audit.commands')">
        <t-card :bordered="false">
          <template #actions>
            <t-button variant="outline" @click="onExport">{{ $t('audit.exportData') }}</t-button>
          </template>
          <t-table :data="commands" :columns="commandColumns" :loading="cmdLoading" row-key="id" />
        </t-card>
      </t-tab-panel>
      <t-tab-panel value="risk" :label="$t('audit.riskCommands')">
        <t-card :bordered="false">
          <t-table :data="riskCommands" :columns="commandColumns" :loading="riskLoading" row-key="id" />
        </t-card>
      </t-tab-panel>
      <t-tab-panel value="loginLogs" :label="$t('audit.loginLogs')">
        <t-card :bordered="false">
          <t-table :data="loginLogs" :columns="loginColumns" :loading="logLoading" row-key="id" />
        </t-card>
      </t-tab-panel>
    </t-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import { auditApi } from '@/api';

const activeTab = ref('sessions');
const sessions = ref<any[]>([]);
const commands = ref<any[]>([]);
const riskCommands = ref<any[]>([]);
const loginLogs = ref<any[]>([]);
const loading = ref(false);
const cmdLoading = ref(false);
const riskLoading = ref(false);
const logLoading = ref(false);

const sessionColumns = [
  { colKey: 'session_id', title: 'Session ID', width: 200, ellipsis: true },
  { colKey: 'client_ip', title: 'IP', width: 120 },
  { colKey: 'status', title: '状态', width: 80 },
  { colKey: 'started_at', title: '开始时间', width: 180 },
  { colKey: 'ended_at', title: '结束时间', width: 180 },
  { colKey: 'duration_seconds', title: '时长(s)', width: 80 },
];

const commandColumns = [
  { colKey: 'command', title: '命令', ellipsis: true },
  { colKey: 'risk_level', title: '风险', width: 80,
    cell: (h: any, { row }: any) => h('t-tag', { props: { theme: row.risk_level === 'danger' ? 'danger' : row.risk_level === 'warning' ? 'warning' : 'default', size: 'small' } }, row.risk_level)
  },
  { colKey: 'is_blocked', title: '拦截', width: 60 },
  { colKey: 'executed_at', title: '时间', width: 180 },
];

const loginColumns = [
  { colKey: 'username', title: '用户', width: 100 },
  { colKey: 'login_ip', title: 'IP', width: 120 },
  { colKey: 'is_success', title: '成功', width: 60 },
  { colKey: 'login_method', title: '方式', width: 80 },
  { colKey: 'login_at', title: '时间', width: 180 },
];

async function loadData() {
  loading.value = true;
  try { sessions.value = await auditApi.listSessions(); } finally { loading.value = false; }
}

async function loadCommands() {
  cmdLoading.value = true;
  try { commands.value = await auditApi.listCommands(); } finally { cmdLoading.value = false; }
}

async function loadRiskCommands() {
  riskLoading.value = true;
  try { riskCommands.value = await auditApi.listRiskCommands(); } finally { riskLoading.value = false; }
}

async function loadLoginLogs() {
  logLoading.value = true;
  try { loginLogs.value = await auditApi.listLoginLogs(); } finally { logLoading.value = false; }
}

async function onExport() {
  try {
    const res: any = await auditApi.exportCommands({ format: 'json' });
    const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'audit_commands.json'; a.click();
    URL.revokeObjectURL(url);
  } catch (e) { /* handled */ }
}

watch(activeTab, (val) => {
  if (val === 'sessions') loadData();
  else if (val === 'commands') loadCommands();
  else if (val === 'risk') loadRiskCommands();
  else if (val === 'loginLogs') loadLoginLogs();
});

onMounted(() => loadData());
</script>
