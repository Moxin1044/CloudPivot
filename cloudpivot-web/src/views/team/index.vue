<template>
  <div class="team-page">
    <t-card :bordered="false" :title="$t('team.title')">
      <template #actions>
        <t-button theme="primary" @click="showCreate = true">
          <template #icon><t-icon name="add" /></template>
          {{ $t('common.create') }}
        </t-button>
      </template>
      <t-table :data="teams" :columns="columns" :loading="loading" row-key="id" />
    </t-card>

    <t-dialog v-model:visible="showCreate" :header="$t('team.createTeam')" @confirm="onCreate">
      <t-form :data="formData" label-align="top">
        <t-form-item :label="$t('common.name')"><t-input v-model="formData.name" /></t-form-item>
        <t-form-item :label="$t('common.description')"><t-textarea v-model="formData.description" /></t-form-item>
      </t-form>
    </t-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { MessagePlugin } from 'tdesign-vue-next';
import { useI18n } from 'vue-i18n';
import { teamApi } from '@/api';

const { t } = useI18n();
const teams = ref<any[]>([]);
const loading = ref(false);
const showCreate = ref(false);
const formData = reactive({ name: '', description: '' });

const columns = [
  { colKey: 'name', title: t('common.name') },
  { colKey: 'description', title: t('common.description') },
  { colKey: 'is_active', title: t('common.status'),
    cell: (h: any, { row }: any) => h('t-tag', { props: { theme: row.is_active ? 'success' : 'danger', size: 'small' } }, row.is_active ? t('common.enabled') : t('common.disabled'))
  },
  { colKey: 'created_at', title: t('common.createdAt') },
  { colKey: 'actions', title: t('common.actions'),
    cell: (_h: any, { row }: any) => _h('div', { style: 'display:flex;gap:8px' }, [
      _h('t-button', { props: { variant: 'text', theme: 'primary', size: 'small' }, on: { click: () => viewMembers(row.id) } }, t('team.memberBtn')),
      _h('t-button', { props: { variant: 'text', theme: 'danger', size: 'small' }, on: { click: () => onDelete(row.id) } }, t('common.delete')),
    ])
  },
];

async function loadData() {
  loading.value = true;
  try { teams.value = await teamApi.list(); } finally { loading.value = false; }
}

async function onCreate() {
  try {
    await teamApi.create(formData);
    MessagePlugin.success(t('team.teamCreated'));
    showCreate.value = false;
    loadData();
  } catch (e) { /* handled */ }
}

async function onDelete(id: number) {
  await teamApi.delete(id);
  MessagePlugin.success(t('team.teamDeleted'));
  loadData();
}

function viewMembers(id: number) {
  // Could open a dialog or navigate
}

onMounted(() => loadData());
</script>
