<template>
  <div class="user-page">
    <t-card :title="$t('settings.userManagement')" :bordered="false">
      <template #actions>
        <t-button theme="primary" @click="onOpenCreate">
          <t-icon name="add" />
          {{ $t('settings.createUser') }}
        </t-button>
      </template>
      <t-table
        :data="userList"
        :columns="columns"
        :loading="loading"
        row-key="id"
        :pagination="pagination"
        @page-change="onPageChange"
      >
        <template #role="{ row }">
          <t-tag :theme="roleTheme(row.role)" variant="light">
            {{ $t(`team.${row.role}`) }}
          </t-tag>
        </template>
        <template #status="{ row }">
          <t-tag :theme="statusTheme(row.status)" variant="light">
            {{ $t(`settings.${row.status}`) }}
          </t-tag>
        </template>
        <template #last_login_at="{ row }">
          {{ row.last_login_at ? formatDate(row.last_login_at) : '-' }}
        </template>
        <template #created_at="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
        <template #op="{ row }">
          <t-space>
            <t-button variant="text" theme="primary" size="small" @click="onEdit(row)">
              {{ $t('common.edit') }}
            </t-button>
            <t-button variant="text" theme="danger" size="small" @click="onDelete(row)">
              {{ $t('common.delete') }}
            </t-button>
          </t-space>
        </template>
      </t-table>
    </t-card>

    <!-- Create/Edit Dialog -->
    <t-dialog
      v-model:visible="dialogVisible"
      :header="dialogTitle"
      :confirm-btn="{ loading: dialogLoading }"
      @confirm="onSave"
    >
      <t-form :data="formData" label-align="top">
        <t-form-item :label="$t('settings.username')" name="username">
          <t-input v-model="formData.username" :disabled="isEdit" />
        </t-form-item>
        <t-form-item :label="$t('common.email')" name="email">
          <t-input v-model="formData.email" />
        </t-form-item>
        <t-form-item :label="$t('settings.userRole')" name="role">
          <t-select v-model="formData.role" :options="roleOptions" />
        </t-form-item>
        <t-form-item :label="$t('settings.userStatus')" name="status">
          <t-select v-model="formData.status" :options="statusOptions" />
        </t-form-item>
        <t-form-item :label="$t('login.password')" name="password">
          <t-input v-model="formData.password" type="password" :placeholder="isEdit ? $t('settings.leaveBlank') : ''" />
          <div v-if="isEdit" class="form-tip">{{ $t('settings.leaveBlank') }}</div>
        </t-form-item>
      </t-form>
    </t-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { MessagePlugin, DialogPlugin } from 'tdesign-vue-next';
import { userApi } from '@/api';

const { t } = useI18n();
const loading = ref(false);
const userList = ref<any[]>([]);
const pagination = reactive({ current: 1, pageSize: 20, total: 0 });

const dialogVisible = ref(false);
const dialogLoading = ref(false);
const isEdit = ref(false);
const editingId = ref<number | null>(null);

const formData = reactive({
  username: '',
  email: '',
  role: 'viewer',
  status: 'active',
  password: '',
});

const dialogTitle = computed(() =>
  isEdit.value ? t('common.edit') : t('settings.createUser')
);

const roleOptions = [
  { label: t('team.admin'), value: 'admin' },
  { label: t('team.operator'), value: 'operator' },
  { label: t('team.viewer'), value: 'viewer' },
];

const statusOptions = [
  { label: t('settings.active'), value: 'active' },
  { label: t('settings.disabled'), value: 'disabled' },
  { label: t('settings.locked'), value: 'locked' },
];

const columns = [
  { colKey: 'id', title: 'ID', width: 80 },
  { colKey: 'username', title: t('settings.username'), width: 140 },
  { colKey: 'email', title: t('common.email'), width: 200 },
  { colKey: 'display_name', title: t('common.name'), width: 140 },
  { colKey: 'role', title: t('settings.userRole'), width: 120 },
  { colKey: 'status', title: t('settings.userStatus'), width: 100 },
  { colKey: 'last_login_at', title: t('settings.lastLoginAt'), width: 170 },
  { colKey: 'created_at', title: t('common.createdAt'), width: 170 },
  { colKey: 'op', title: t('common.actions'), width: 140, fixed: 'right' },
];

function roleTheme(role: string) {
  if (role === 'admin') return 'danger';
  if (role === 'operator') return 'warning';
  return 'default';
}

function statusTheme(status: string) {
  if (status === 'active') return 'success';
  if (status === 'disabled') return 'warning';
  return 'danger';
}

function formatDate(val: string) {
  if (!val) return '-';
  const d = new Date(val);
  return d.toLocaleString();
}

async function loadData() {
  loading.value = true;
  try {
    const res: any = await userApi.list({
      skip: (pagination.current - 1) * pagination.pageSize,
      limit: pagination.pageSize,
    });
    userList.value = res;
    pagination.total = res.length === pagination.pageSize
      ? pagination.current * pagination.pageSize + 1
      : (pagination.current - 1) * pagination.pageSize + res.length;
  } catch (e) { /* handled */ }
  finally { loading.value = false; }
}

function onPageChange(pageInfo: any) {
  pagination.current = pageInfo.current;
  pagination.pageSize = pageInfo.pageSize;
  loadData();
}

function resetForm() {
  formData.username = '';
  formData.email = '';
  formData.role = 'viewer';
  formData.status = 'active';
  formData.password = '';
}

function onOpenCreate() {
  isEdit.value = false;
  editingId.value = null;
  resetForm();
  dialogVisible.value = true;
}

function onEdit(row: any) {
  isEdit.value = true;
  editingId.value = row.id;
  formData.username = row.username;
  formData.email = row.email;
  formData.role = row.role;
  formData.status = row.status;
  formData.password = '';
  dialogVisible.value = true;
}

async function onSave() {
  dialogLoading.value = true;
  try {
    const payload: any = {
      email: formData.email,
      role: formData.role,
      status: formData.status,
    };
    if (formData.password) {
      payload.password = formData.password;
    }
    if (isEdit.value && editingId.value !== null) {
      await userApi.update(editingId.value, payload);
      MessagePlugin.success(t('settings.userUpdated'));
    } else {
      await userApi.create({
        username: formData.username,
        email: formData.email,
        password: formData.password,
        role: formData.role,
        status: formData.status,
      });
      MessagePlugin.success(t('settings.userCreated'));
    }
    dialogVisible.value = false;
    loadData();
  } catch (e) { /* handled */ }
  finally { dialogLoading.value = false; }
}

function onDelete(row: any) {
  const confirmDialog = DialogPlugin.confirm({
    header: t('common.confirm'),
    body: t('settings.confirmDeleteUser'),
    onConfirm: async () => {
      try {
        await userApi.delete(row.id);
        MessagePlugin.success(t('settings.userDeleted'));
        loadData();
      } catch (e) { /* handled */ }
      confirmDialog.destroy();
    },
    onClose: () => confirmDialog.destroy(),
  });
}

onMounted(() => {
  loadData();
});
</script>

<style scoped>
.form-tip {
  font-size: 12px;
  color: var(--td-text-color-placeholder);
  margin-top: 4px;
}
</style>
