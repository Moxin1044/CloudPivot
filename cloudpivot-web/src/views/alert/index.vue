<template>
  <div class="alert-page">
    <t-card :bordered="false">
      <template #title>{{ $t('alert.title') }}</template>
      <template #actions>
        <t-select v-model="filterStatus" :options="statusOptions" style="width:120px" @change="loadData" />
      </template>
      <t-table :data="alerts" :columns="columns" :loading="loading" row-key="id" />
    </t-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { MessagePlugin } from 'tdesign-vue-next';
import { monitorApi } from '@/api';

const alerts = ref<any[]>([]);
const loading = ref(false);
const filterStatus = ref('');

const statusOptions = [
  { label: '全部', value: '' },
  { label: '待处理', value: 'pending' },
  { label: '已确认', value: 'acknowledged' },
  { label: '已解决', value: 'resolved' },
];

const columns = [
  { colKey: 'id', title: 'ID', width: 60 },
  { colKey: 'title', title: '告警', ellipsis: true },
  { colKey: 'severity', title: '严重程度', width: 100,
    cell: (h: any, { row }: any) => h('t-tag', { props: { theme: row.severity === 'critical' ? 'danger' : row.severity === 'warning' ? 'warning' : 'default', size: 'small' } }, row.severity)
  },
  { colKey: 'status', title: '状态', width: 80,
    cell: (h: any, { row }: any) => h('t-tag', { props: { theme: row.status === 'pending' ? 'warning' : row.status === 'resolved' ? 'success' : 'default', size: 'small' } }, row.status)
  },
  { colKey: 'message', title: '详情', ellipsis: true },
  { colKey: 'created_at', title: '时间', width: 180 },
  { colKey: 'actions', title: '操作', width: 150,
    cell: (_h: any, { row }: any) => _h('div', { style: 'display:flex;gap:8px' }, [
      row.status === 'pending' ? _h('t-button', { props: { size: 'small', variant: 'text', theme: 'primary' }, on: { click: () => onAck(row.id) } }, '确认') : null,
      row.status !== 'resolved' ? _h('t-button', { props: { size: 'small', variant: 'text', theme: 'success' }, on: { click: () => onResolve(row.id) } }, '解决') : null,
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
  MessagePlugin.success('已确认');
  loadData();
}

async function onResolve(id: number) {
  await monitorApi.resolveAlert(id);
  MessagePlugin.success('已解决');
  loadData();
}

onMounted(() => loadData());
</script>
