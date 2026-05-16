<template>
  <div class="audit-page">
    <t-tabs v-model="activeTab">
      <t-tab-panel value="sessions" :label="$t('audit.sessions')">
        <t-card :bordered="false">
          <template #actions>
            <t-input v-model="sessionSearch" placeholder="搜索 Session ID / IP" clearable style="width: 260px" @enter="onSessionSearch" @clear="onSessionSearch">
              <template #suffix><t-button variant="text" size="small" @click="onSessionSearch"><t-icon name="search" /></t-button></template>
            </t-input>
          </template>
          <t-table
            :data="sessions"
            :columns="sessionColumns"
            :loading="loading"
            row-key="id"
            :pagination="sessionPagination"
            @page-change="onSessionPageChange"
          >
            <template #actions="{ row }">
              <t-button variant="outline" theme="primary" size="small" @click="viewSession(row.id)">{{ $t('common.detail') }}</t-button>
            </template>
          </t-table>
        </t-card>
      </t-tab-panel>
      <t-tab-panel value="commands" :label="$t('audit.commands')">
        <t-card :bordered="false">
          <template #actions>
            <t-space>
              <t-input v-model="commandSearch" placeholder="搜索命令" clearable style="width: 260px" @enter="onCommandSearch" @clear="onCommandSearch">
                <template #suffix><t-button variant="text" size="small" @click="onCommandSearch"><t-icon name="search" /></t-button></template>
              </t-input>
              <t-button variant="outline" @click="onExport">{{ $t('audit.exportData') }}</t-button>
            </t-space>
          </template>
          <t-table
            :data="commands"
            :columns="commandColumns"
            :loading="cmdLoading"
            row-key="id"
            :pagination="commandPagination"
            @page-change="onCommandPageChange"
          >
            <template #actions="{ row }">
              <t-button variant="outline" theme="primary" size="small" @click="viewCommand(row.id)">{{ $t('common.detail') }}</t-button>
            </template>
          </t-table>
        </t-card>
      </t-tab-panel>
      <t-tab-panel value="risk" :label="$t('audit.riskCommands')">
        <t-card :bordered="false">
          <template #actions>
            <t-input v-model="riskSearch" placeholder="搜索命令" clearable style="width: 260px" @enter="onRiskSearch" @clear="onRiskSearch">
              <template #suffix><t-button variant="text" size="small" @click="onRiskSearch"><t-icon name="search" /></t-button></template>
            </t-input>
          </template>
          <t-table
            :data="riskCommands"
            :columns="commandColumns"
            :loading="riskLoading"
            row-key="id"
            :pagination="riskPagination"
            @page-change="onRiskPageChange"
          >
            <template #actions="{ row }">
              <t-button variant="outline" theme="primary" size="small" @click="viewCommand(row.id)">{{ $t('common.detail') }}</t-button>
            </template>
          </t-table>
        </t-card>
      </t-tab-panel>
      <t-tab-panel value="loginLogs" :label="$t('audit.loginLogs')">
        <t-card :bordered="false">
          <template #actions>
            <t-input v-model="logSearch" placeholder="搜索用户 / IP" clearable style="width: 260px" @enter="onLogSearch" @clear="onLogSearch">
              <template #suffix><t-button variant="text" size="small" @click="onLogSearch"><t-icon name="search" /></t-button></template>
            </t-input>
          </template>
          <t-table
            :data="loginLogs"
            :columns="loginColumns"
            :loading="logLoading"
            row-key="id"
            :pagination="logPagination"
            @page-change="onLogPageChange"
          >
            <template #actions="{ row }">
              <t-button variant="outline" theme="primary" size="small" @click="viewLogin(row.id)">{{ $t('common.detail') }}</t-button>
            </template>
          </t-table>
        </t-card>
      </t-tab-panel>
      <t-tab-panel value="sshLoginLogs" label="SSH登录分析">
        <ssh-login-logs />
      </t-tab-panel>
    </t-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, defineAsyncComponent, reactive } from 'vue';
import { useI18n } from 'vue-i18n';
import { MessagePlugin } from 'tdesign-vue-next';
import { auditApi } from '@/api';

const SshLoginLogs = defineAsyncComponent(() => import('./sshLoginLogs.vue'));

const { t } = useI18n();
const activeTab = ref('sessions');
const sessions = ref<any[]>([]);
const commands = ref<any[]>([]);
const riskCommands = ref<any[]>([]);
const loginLogs = ref<any[]>([]);
const loading = ref(false);
const cmdLoading = ref(false);
const riskLoading = ref(false);
const logLoading = ref(false);

const sessionSearch = ref('');
const commandSearch = ref('');
const riskSearch = ref('');
const logSearch = ref('');

const sessionPagination = reactive({ current: 1, pageSize: 20, total: 0 });
const commandPagination = reactive({ current: 1, pageSize: 20, total: 0 });
const riskPagination = reactive({ current: 1, pageSize: 20, total: 0 });
const logPagination = reactive({ current: 1, pageSize: 20, total: 0 });

const sessionColumns = [
  { colKey: 'session_id', title: t('audit.sessionId'), width: 200, ellipsis: true },
  { colKey: 'client_ip', title: t('audit.clientIp'), width: 120 },
  { colKey: 'status', title: t('audit.status'), width: 80 },
  { colKey: 'started_at', title: t('audit.startedAt'), width: 180 },
  { colKey: 'ended_at', title: t('audit.endedAt'), width: 180 },
  { colKey: 'duration_seconds', title: t('audit.duration'), width: 80 },
  { colKey: 'actions', title: t('common.actions'), width: 100 },
];

const commandColumns = [
  { colKey: 'command', title: t('audit.command'), ellipsis: true },
  { colKey: 'risk_level', title: t('audit.riskLevel'), width: 80,
    cell: (h: any, { row }: any) => h('t-tag', { theme: row.risk_level === 'danger' ? 'danger' : row.risk_level === 'warning' ? 'warning' : 'default', size: 'small' }, row.risk_level)
  },
  { colKey: 'is_blocked', title: t('audit.isBlocked'), width: 60 },
  { colKey: 'executed_at', title: t('audit.executedAt'), width: 180 },
  { colKey: 'actions', title: t('common.actions'), width: 100 },
];

const loginColumns = [
  { colKey: 'username', title: t('audit.username'), width: 100 },
  { colKey: 'login_ip', title: t('audit.loginIp'), width: 120 },
  { colKey: 'is_success', title: t('audit.success'), width: 60 },
  { colKey: 'login_method', title: t('audit.method'), width: 80 },
  { colKey: 'login_at', title: t('audit.loginAt'), width: 180 },
  { colKey: 'actions', title: t('common.actions'), width: 100 },
];

async function loadData() {
  loading.value = true;
  try {
    const res: any = await auditApi.listSessions({
      skip: (sessionPagination.current - 1) * sessionPagination.pageSize,
      limit: sessionPagination.pageSize,
      keyword: sessionSearch.value || undefined,
    });
    sessions.value = res.items || [];
    sessionPagination.total = res.total || 0;
  } finally { loading.value = false; }
}

async function loadCommands() {
  cmdLoading.value = true;
  try {
    const res: any = await auditApi.listCommands({
      skip: (commandPagination.current - 1) * commandPagination.pageSize,
      limit: commandPagination.pageSize,
      keyword: commandSearch.value || undefined,
    });
    commands.value = res.items || [];
    commandPagination.total = res.total || 0;
  } finally { cmdLoading.value = false; }
}

async function loadRiskCommands() {
  riskLoading.value = true;
  try {
    const res: any = await auditApi.listRiskCommands({
      skip: (riskPagination.current - 1) * riskPagination.pageSize,
      limit: riskPagination.pageSize,
      keyword: riskSearch.value || undefined,
    });
    riskCommands.value = res.items || [];
    riskPagination.total = res.total || 0;
  } finally { riskLoading.value = false; }
}

async function loadLoginLogs() {
  logLoading.value = true;
  try {
    const res: any = await auditApi.listLoginLogs({
      skip: (logPagination.current - 1) * logPagination.pageSize,
      limit: logPagination.pageSize,
      keyword: logSearch.value || undefined,
    });
    loginLogs.value = res.items || [];
    logPagination.total = res.total || 0;
  } finally { logLoading.value = false; }
}

function onSessionSearch() { sessionPagination.current = 1; loadData(); }
function onCommandSearch() { commandPagination.current = 1; loadCommands(); }
function onRiskSearch() { riskPagination.current = 1; loadRiskCommands(); }
function onLogSearch() { logPagination.current = 1; loadLoginLogs(); }

function onSessionPageChange(p: any) { sessionPagination.current = p.current; sessionPagination.pageSize = p.pageSize; loadData(); }
function onCommandPageChange(p: any) { commandPagination.current = p.current; commandPagination.pageSize = p.pageSize; loadCommands(); }
function onRiskPageChange(p: any) { riskPagination.current = p.current; riskPagination.pageSize = p.pageSize; loadRiskCommands(); }
function onLogPageChange(p: any) { logPagination.current = p.current; logPagination.pageSize = p.pageSize; loadLoginLogs(); }

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

function viewSession(id: number) {
  MessagePlugin.info('Session detail coming soon');
}

function viewCommand(id: number) {
  MessagePlugin.info('Command detail coming soon');
}

function viewLogin(id: number) {
  MessagePlugin.info('Login log detail coming soon');
}

watch(activeTab, (val) => {
  if (val === 'sessions') loadData();
  else if (val === 'commands') loadCommands();
  else if (val === 'risk') loadRiskCommands();
  else if (val === 'loginLogs') loadLoginLogs();
});

onMounted(() => loadData());
</script>
