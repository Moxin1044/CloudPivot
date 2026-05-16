<template>
  <div class="permission-page">
    <t-tabs v-model="activeTab">
      <t-tab-panel value="permissions" :label="$t('permission.title')">
        <t-card :bordered="false">
          <template #actions>
            <t-button theme="primary" @click="showCreate = true">{{ $t('common.create') }}</t-button>
          </template>
          <t-table :data="permissions" :columns="permColumns" :loading="loading" row-key="id" />
        </t-card>
      </t-tab-panel>
      <t-tab-panel value="temporary" :label="$t('permission.temporaryAuth')">
        <t-card :bordered="false">
          <template #actions>
            <t-button theme="primary" @click="showTempCreate = true">{{ $t('common.create') }}</t-button>
          </template>
          <t-table :data="tempPerms" :columns="tempColumns" :loading="tempLoading" row-key="id" />
        </t-card>
      </t-tab-panel>
    </t-tabs>

    <t-dialog v-model:visible="showCreate" :header="$t('permission.createPermission')" @confirm="onCreatePerm">
      <t-form :data="permForm" label-align="top">
        <t-form-item :label="$t('permission.hostId')"><t-input-number v-model="permForm.host_id" /></t-form-item>
        <t-form-item :label="$t('permission.teamId')"><t-input-number v-model="permForm.team_id" /></t-form-item>
        <t-form-item :label="$t('permission.permissionLevel')">
          <t-select v-model="permForm.permission_level" :options="levelOptions" />
        </t-form-item>
        <t-form-item :label="$t('permission.allowUpload')"><t-switch v-model="permForm.can_upload" /></t-form-item>
        <t-form-item :label="$t('permission.allowDownload')"><t-switch v-model="permForm.can_download" /></t-form-item>
        <t-form-item :label="$t('permission.allowExecute')"><t-switch v-model="permForm.can_execute" /></t-form-item>
      </t-form>
    </t-dialog>

    <t-dialog v-model:visible="showTempCreate" :header="$t('permission.createTempAuth')" @confirm="onCreateTemp">
      <t-form :data="tempForm" label-align="top">
        <t-form-item :label="$t('permission.hostId')"><t-input-number v-model="tempForm.host_id" /></t-form-item>
        <t-form-item :label="$t('permission.userId')"><t-input-number v-model="tempForm.user_id" /></t-form-item>
        <t-form-item :label="$t('permission.permissionLevel')"><t-select v-model="tempForm.permission_level" :options="levelOptions" /></t-form-item>
        <t-form-item :label="$t('permission.expiresAt')"><t-date-picker v-model="tempForm.expires_at" enable-time-picker /></t-form-item>
        <t-form-item :label="$t('permission.reason')"><t-textarea v-model="tempForm.reason" /></t-form-item>
      </t-form>
    </t-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { MessagePlugin } from 'tdesign-vue-next';
import { useI18n } from 'vue-i18n';
import { permissionApi } from '@/api';

const { t } = useI18n();
const activeTab = ref('permissions');
const permissions = ref<any[]>([]);
const tempPerms = ref<any[]>([]);
const loading = ref(false);
const tempLoading = ref(false);
const showCreate = ref(false);
const showTempCreate = ref(false);

const levelOptions = [
  { label: t('permission.readonly'), value: 'readonly' },
  { label: t('permission.readExecute'), value: 'read_execute' },
  { label: t('permission.readExecuteUpload'), value: 'read_execute_upload' },
  { label: t('permission.full'), value: 'full' },
];

const permForm = reactive({
  host_id: 0, team_id: null as number | null, permission_level: 'read_execute',
  can_upload: false, can_download: false, can_execute: true,
});
const tempForm = reactive({
  host_id: 0, user_id: 0, permission_level: 'read_execute',
  expires_at: '', reason: '',
});

const permColumns = [
  { colKey: 'id', title: 'ID', width: 60 },
  { colKey: 'host_id', title: t('permission.hostId'), width: 80 },
  { colKey: 'team_id', title: t('permission.teamId'), width: 80 },
  { colKey: 'permission_level', title: t('permission.permissionLevel') },
  { colKey: 'can_upload', title: t('permission.canUpload') },
  { colKey: 'can_download', title: t('permission.canDownload') },
  { colKey: 'can_execute', title: t('permission.canExecute') },
  { colKey: 'is_active', title: t('common.status') },
  { colKey: 'actions', title: t('common.actions'), width: 100,
    cell: (_h: any, { row }: any) => _h('t-button', { variant: 'outline', theme: 'danger', size: 'small', onClick: () => onDeletePerm(row.id) }, t('common.delete'))
  },
];

const tempColumns = [
  { colKey: 'id', title: 'ID', width: 60 },
  { colKey: 'host_id', title: t('permission.hostId'), width: 80 },
  { colKey: 'user_id', title: t('permission.userId'), width: 80 },
  { colKey: 'permission_level', title: t('permission.level') },
  { colKey: 'expires_at', title: t('permission.expiresAt') },
  { colKey: 'is_revoked', title: t('permission.revoked') },
  { colKey: 'actions', title: t('common.actions'), width: 100,
    cell: (_h: any, { row }: any) => _h('t-button', { variant: 'outline', theme: 'danger', size: 'small', onClick: () => onRevokeTemp(row.id) }, t('permission.revokeBtn'))
  },
];

async function loadData() {
  loading.value = true;
  try { permissions.value = await permissionApi.list(); } finally { loading.value = false; }
}

async function loadTempData() {
  tempLoading.value = true;
  try { tempPerms.value = await permissionApi.listTemporary(); } finally { tempLoading.value = false; }
}

async function onCreatePerm() {
  await permissionApi.create(permForm);
  MessagePlugin.success(t('permission.permCreated'));
  showCreate.value = false;
  loadData();
}

async function onDeletePerm(id: number) {
  await permissionApi.delete(id);
  loadData();
}

async function onCreateTemp() {
  await permissionApi.createTemporary(tempForm);
  MessagePlugin.success(t('permission.permCreated'));
  showTempCreate.value = false;
  loadTempData();
}

async function onRevokeTemp(id: number) {
  await permissionApi.revokeTemporary(id);
  loadTempData();
}

onMounted(() => { loadData(); loadTempData(); });
</script>
