<template>
  <div class="host-page">
    <t-card :bordered="false" :title="$t('host.title')">
      <template #actions>
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
          <t-input v-model="searchKeyword" placeholder="搜索名称 / IP / 系统 / 公网IP" clearable style="width: 280px" @enter="onSearch" @clear="onSearch">
            <template #suffix><t-button variant="text" size="small" @click="onSearch"><t-icon name="search" /></t-button></template>
          </t-input>
          <t-button theme="primary" @click="showCreate = true">
            <template #icon><t-icon name="add" /></template>
            {{ $t('common.create') }}
          </t-button>
          <t-button variant="outline" @click="showImport = true">
            <template #icon><t-icon name="upload" /></template>
            {{ $t('host.batchImport') }}
          </t-button>
          <t-button variant="outline" @click="loadData">
            <template #icon><t-icon name="refresh" /></template>
          </t-button>
        </div>
      </template>
      <t-table
        :data="hosts"
        :columns="columns"
        :loading="loading"
        :pagination="pagination"
        @page-change="onPageChange"
        row-key="id"
      />
    </t-card>

    <!-- Create Dialog -->
    <t-dialog v-model:visible="showCreate" :header="$t('host.createHost')" @confirm="onCreate" :confirm-btn="{ loading: createLoading }">
      <t-form :data="formData" label-align="top">
        <t-form-item :label="$t('common.name')"><t-input v-model="formData.name" /></t-form-item>
        <t-form-item :label="$t('host.hostname')"><t-input v-model="formData.hostname" /></t-form-item>
        <t-form-item :label="$t('host.ip')"><t-input v-model="formData.ip_address" /></t-form-item>
        <t-form-item :label="$t('host.port')"><t-input-number v-model="formData.port" :min="1" :max="65535" /></t-form-item>
        <t-form-item :label="$t('host.username')"><t-input v-model="formData.username" /></t-form-item>
        <t-form-item :label="$t('host.authType')">
          <t-radio-group v-model="formData.auth_type">
            <t-radio-button value="password">{{ $t('host.passwordAuth') }}</t-radio-button>
            <t-radio-button value="key">{{ $t('host.keyAuth') }}</t-radio-button>
          </t-radio-group>
        </t-form-item>
        <t-form-item v-if="formData.auth_type === 'password'" :label="$t('host.password')">
          <t-input v-model="formData.password" type="password" />
        </t-form-item>
        <t-form-item v-else :label="$t('host.privateKey')">
          <t-textarea v-model="formData.private_key" :autosize="{ minRows: 3, maxRows: 6 }" />
          <div style="margin-top:8px">
            <t-button variant="outline" size="small" @click="keyFileInput?.click()">
              <template #icon><t-icon name="upload" /></template>
              {{ $t('host.uploadKey') }}
            </t-button>
            <input ref="keyFileInput" type="file" style="display:none" accept=".pem,.key,.ppk,text/plain" @change="onKeyFileChange" />
          </div>
        </t-form-item>
        <t-form-item :label="$t('common.description')"><t-textarea v-model="formData.description" /></t-form-item>
      </t-form>
    </t-dialog>

    <!-- Import Dialog -->
    <t-dialog v-model:visible="showImport" :header="$t('host.importHosts')" @confirm="onImport" :confirm-btn="{ loading: importLoading }">
      <t-textarea v-model="importJson" :placeholder="$t('host.importHosts')" :autosize="{ minRows: 6, maxRows: 15 }" />
    </t-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onBeforeUnmount, h } from 'vue';
import { useRouter } from 'vue-router';
import { MessagePlugin } from 'tdesign-vue-next';
import { useI18n } from 'vue-i18n';
import { hostApi } from '@/api';

const router = useRouter();
const { t } = useI18n();
const hosts = ref<any[]>([]);
const loading = ref(false);
const showCreate = ref(false);
const showImport = ref(false);
const createLoading = ref(false);
const importLoading = ref(false);
const importJson = ref('');

const pagination = reactive({ current: 1, pageSize: 20, total: 0 });
const searchKeyword = ref('');

const formData = reactive({
  name: '', hostname: '', ip_address: '', port: 22,
  auth_type: 'password', username: '', password: '', private_key: '', description: '',
});
const keyFileInput = ref<HTMLInputElement>();

const columns = [
  { colKey: 'name', title: t('common.name'), width: 150 },
  { colKey: 'ip_address', title: t('host.ip'), width: 130 },
  { colKey: 'public_ip', title: t('host.publicIp'), width: 130 },
  { colKey: 'os_name', title: t('host.osName'), width: 100 },
  { colKey: 'os_version', title: t('host.osVersion'), width: 100 },
  { colKey: 'port', title: t('host.port'), width: 70 },
  { colKey: 'username', title: t('host.username'), width: 100 },
  { colKey: 'status', title: t('common.status'), width: 90,
    cell: (h: any, { row }: any) => h('t-tag', {
      props: { theme: row.status === 'online' ? 'success' : row.status === 'offline' ? 'danger' : 'default', size: 'small' }
    }, row.status === 'online' ? t('host.statusOnline') : row.status === 'offline' ? t('host.statusOffline') : t('host.statusUnknown'))
  },
  { colKey: 'auth_type', title: t('host.authType'), width: 70 },
  { colKey: 'actions', title: t('common.actions'), width: 220,
    cell: (_h: any, { row }: any) => {
      return h('div', { style: 'display:flex;gap:8px' }, [
        h('t-button', { variant: 'text', theme: 'primary', size: 'small', onClick: () => router.push(`/hosts/${row.id}`) }, t('host.detailBtn')),
        h('t-button', { variant: 'text', theme: 'primary', size: 'small', onClick: () => onTest(row.id) }, t('host.testBtn')),
        h('t-button', { variant: 'text', theme: 'danger', size: 'small', onClick: () => onDelete(row.id) }, t('host.deleteBtn')),
      ]);
    }
  },
];

async function loadData() {
  loading.value = true;
  try {
    const res: any = await hostApi.list({
      skip: (pagination.current - 1) * pagination.pageSize,
      limit: pagination.pageSize,
      keyword: searchKeyword.value || undefined,
    });
    hosts.value = res.items || [];
    pagination.total = res.total || 0;
  } finally {
    loading.value = false;
  }
}

function onSearch() {
  pagination.current = 1;
  loadData();
}

function onPageChange({ current, pageSize }: any) {
  pagination.current = current;
  pagination.pageSize = pageSize;
  loadData();
}

async function onCreate() {
  createLoading.value = true;
  try {
    const res: any = await hostApi.create(formData);
    MessagePlugin.success(t('host.hostCreated'));
    showCreate.value = false;
    // 创建后自动测试连接并获取系统信息
    const hostId = res?.id || res?.data?.id;
    if (hostId) {
      try {
        const testRes: any = await hostApi.testConnectivity(hostId);
        if (testRes.success) {
          MessagePlugin.success('已自动获取系统信息');
        }
      } catch (e) { /* ignore auto-test error */ }
    }
    loadData();
  } finally {
    createLoading.value = false;
  }
}

async function onTest(id: number) {
  try {
    const res: any = await hostApi.testConnectivity(id);
    if (res.success) {
      MessagePlugin.success(`${t('host.connectSuccess')} (${res.latency_ms?.toFixed(0)}ms)`);
    } else {
      MessagePlugin.error(`${t('host.connectFailed')}: ${res.message}`);
    }
    loadData();
  } catch (e) { /* handled */ }
}

async function onDelete(id: number) {
  try {
    await hostApi.delete(id);
    MessagePlugin.success(t('host.hostDeleted'));
    loadData();
  } catch (e) { /* handled */ }
}

async function onImport() {
  importLoading.value = true;
  try {
    const parsed = JSON.parse(importJson.value);
    await hostApi.batchImport({ hosts: Array.isArray(parsed) ? parsed : [parsed] });
    MessagePlugin.success(t('host.importSuccess'));
    showImport.value = false;
    loadData();
  } catch (e) {
    MessagePlugin.error(t('host.importFormatError'));
  } finally {
    importLoading.value = false;
  }
}

function onKeyFileChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    formData.private_key = String(reader.result || '');
  };
  reader.readAsText(file);
  (e.target as HTMLInputElement).value = '';
}

let refreshTimer: ReturnType<typeof setInterval>;

onMounted(() => {
  loadData();
  refreshTimer = setInterval(loadData, 15000);
});

onBeforeUnmount(() => {
  clearInterval(refreshTimer);
});
</script>
