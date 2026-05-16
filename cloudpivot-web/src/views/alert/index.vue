<template>
  <div class="alert-page">
    <t-card :bordered="false" :title="$t('alert.title')">
      <template #actions>
        <t-select v-model="filterStatus" :options="statusOptions" style="width:120px" @change="loadData" />
      </template>
      <t-table :data="alerts" :columns="columns" :loading="loading" row-key="id" />
    </t-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { MessagePlugin } from 'tdesign-vue-next';
import { monitorApi } from '@/api';

const { t } = useI18n();
const alerts = ref<any[]>([]);
const loading = ref(false);
const filterStatus = ref('');

const statusOptions = [
  { label: t('alert.allStatus'), value: '' },
  { label: t('alert.pending'), value: 'pending' },
  { label: t('alert.acknowledged'), value: 'acknowledged' },
  { label: t('alert.resolved'), value: 'resolved' },
];

const columns = [
  { colKey: 'id', title: 'ID', width: 60 },
  { colKey: 'title', title: t('alert.alertTitle'), ellipsis: true },
  { colKey: 'severity', title: t('alert.severityLabel'), width: 100,
    cell: (h: any, { row }: any) => h('t-tag', { props: { theme: row.severity === 'critical' ? 'danger' : row.severity === 'warning' ? 'warning' : 'default', size: 'small' } }, row.severity)
  },
  { colKey: 'status', title: t('alert.statusLabel'), width: 80,
    cell: (h: any, { row }: any) => h('t-tag', { props: { theme: row.status === 'pending' ? 'warning' : row.status === 'resolved' ? 'success' : 'default', size: 'small' } }, row.status)
  },
  { colKey: 'message', title: t('alert.messageLabel'), ellipsis: true },
  { colKey: 'created_at', title: t('alert.timeLabel'), width: 180 },
  { colKey: 'actions', title: t('common.actions'), width: 180,
    cell: (_h: any, { row }: any) => _h('div', { style: 'display:flex;gap:8px' }, [
      row.status === 'pending' ? _h('t-button', { size: 'small', variant: 'outline', theme: 'primary', onClick: () => onAck(row.id) }, t('alert.ackBtn')) : null,
      row.status !== 'resolved' ? _h('t-button', { size: 'small', variant: 'outline', theme: 'success', onClick: () => onResolve(row.id) }, t('alert.resolveBtn')) : null,
    ].filter(Boolean))
  },
];

async function loadData() {
  loading.value = true;
  try {
    const params: any = {};
    if (filterStatus.value) params.status = filterStatus.value;
    alerts.value = await monitorApi.listAlerts(params);
  } finally { loading.value = false; }
}

async function onAck(id: number) {
  await monitorApi.acknowledgeAlert(id);
  MessagePlugin.success(t('alert.ackSuccess'));
  loadData();
}

async function onResolve(id: number) {
  await monitorApi.resolveAlert(id);
  MessagePlugin.success(t('alert.resolveSuccess'));
  loadData();
}

onMounted(() => loadData());
</script>
