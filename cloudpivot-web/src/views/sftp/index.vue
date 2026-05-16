<template>
  <div class="sftp-page">
    <t-card :bordered="false" :title="$t('sftp.title')">
      <template #actions>
        <div style="display: flex; gap: 8px; align-items: center;">
          <t-select
            v-model="selectedHostId"
            :options="hostOptions"
            :placeholder="$t('sftp.selectHost')"
            style="width: 250px"
            filterable
            @change="onHostChange"
          />
          <t-button :disabled="!selectedHostId" @click="refreshList" :loading="loading" variant="outline">
            <template #icon><t-icon name="refresh" /></template>
          </t-button>
        </div>
      </template>

      <div v-if="!selectedHostId" class="sftp-placeholder">
        <t-empty :description="$t('sftp.selectHostTip')" />
      </div>

      <template v-else>
        <!-- Breadcrumb Navigation -->
        <div class="sftp-nav">
          <t-breadcrumb>
            <t-breadcrumb-item @click="navigateTo('/')">
              <t-icon name="home" />
            </t-breadcrumb-item>
            <t-breadcrumb-item
              v-for="(part, idx) in pathParts"
              :key="idx"
              @click="navigateTo('/' + pathParts.slice(0, idx + 1).join('/'))"
            >
              {{ part }}
            </t-breadcrumb-item>
          </t-breadcrumb>
        </div>

        <!-- Toolbar -->
        <div class="sftp-toolbar">
          <t-space>
            <t-button theme="primary" size="small" @click="triggerUpload">
              <template #icon><t-icon name="upload" /></template>
              {{ $t('sftp.upload') }}
            </t-button>
            <input ref="uploadInput" type="file" multiple style="display:none" @change="onUpload" />
            <t-button size="small" variant="outline" @click="showMkdir = true">
              <template #icon><t-icon name="folder-add" /></template>
              {{ $t('sftp.newFolder') }}
            </t-button>
            <t-button size="small" variant="outline" theme="danger" :disabled="!selectedFile" @click="onDeleteFile">
              <template #icon><t-icon name="delete" /></template>
              {{ $t('common.delete') }}
            </t-button>
            <t-button size="small" variant="outline" :disabled="!selectedFile" @click="showRename = true">
              <template #icon><t-icon name="edit" /></template>
              {{ $t('sftp.rename') }}
            </t-button>
            <t-button size="small" variant="outline" :disabled="!selectedFile" @click="onCut">
              <template #icon><t-icon name="cut" /></template>
              {{ $t('sftp.cut') }}
            </t-button>
            <t-button size="small" variant="outline" :disabled="!selectedFile" @click="onCopy">
              <template #icon><t-icon name="file-copy" /></template>
              {{ $t('sftp.copy') }}
            </t-button>
            <t-button size="small" variant="outline" :disabled="!selectedFile || selectedFile.is_dir" @click="onDownload">
              <template #icon><t-icon name="download" /></template>
              {{ $t('common.download') }}
            </t-button>
          </t-space>

          <!-- Clipboard actions -->
          <t-space v-if="clipboard.sourcePath" style="margin-left: 12px;">
            <t-tag theme="warning" variant="light">{{ $t('sftp.clipboard') }}: {{ clipboard.name }}</t-tag>
            <t-button size="small" variant="outline" @click="onPaste">{{ $t('sftp.paste') }}</t-button>
            <t-button size="small" variant="outline" @click="clearClipboard">{{ $t('common.cancel') }}</t-button>
          </t-space>
        </div>

        <!-- File List Table -->
        <t-table
          :data="files"
          :columns="columns"
          :loading="loading"
          row-key="path"
          size="small"
          :selected-row-keys="selectedRowKeys"
          @select-change="onSelectChange"
          @row-dblclick="onDblClick"
          hover
          stripe
        />
      </template>
    </t-card>

    <!-- Upload Progress -->
    <t-dialog v-model:visible="uploading" :header="$t('sftp.uploading')" :footer="false" :close-btn="false" width="400px">
      <t-progress :percentage="uploadProgress" />
      <div style="margin-top: 8px; color: var(--td-text-color-secondary);">{{ uploadStatus }}</div>
    </t-dialog>

    <!-- New Folder Dialog -->
    <t-dialog v-model:visible="showMkdir" :header="$t('sftp.newFolder')" @confirm="onMkdir" :confirm-btn="{ loading: mkdirLoading }">
      <t-form :data="mkdirForm" label-align="top">
        <t-form-item :label="$t('sftp.folderName')">
          <t-input v-model="mkdirForm.name" placeholder="new_folder" />
        </t-form-item>
      </t-form>
    </t-dialog>

    <!-- Rename Dialog -->
    <t-dialog v-model:visible="showRename" :header="$t('sftp.rename')" @confirm="onRename" :confirm-btn="{ loading: renameLoading }">
      <t-form :data="renameForm" label-align="top">
        <t-form-item :label="$t('sftp.newName')">
          <t-input v-model="renameForm.new_name" />
        </t-form-item>
      </t-form>
    </t-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { MessagePlugin, DialogPlugin } from 'tdesign-vue-next';
import { hostApi, sftpApi } from '@/api';

const { t } = useI18n();

const selectedHostId = ref<number | undefined>(undefined);
const hostOptions = ref<any[]>([]);
const files = ref<any[]>([]);
const loading = ref(false);
const currentPath = ref('/');

// Selection
const selectedRowKeys = ref<string[]>([]);
const selectedFile = computed(() => {
  if (selectedRowKeys.value.length === 0) return null;
  return files.value.find(f => f.path === selectedRowKeys.value[0]) || null;
});

// Clipboard for copy/cut
const clipboard = reactive({ sourcePath: '', name: '', isCut: false });

// Upload
const uploadInput = ref<HTMLInputElement>();
const uploading = ref(false);
const uploadProgress = ref(0);
const uploadStatus = ref('');

// Dialogs
const showMkdir = ref(false);
const showRename = ref(false);
const mkdirLoading = ref(false);
const renameLoading = ref(false);
const mkdirForm = reactive({ name: '' });
const renameForm = reactive({ new_name: '' });

const pathParts = computed(() => {
  if (currentPath.value === '/') return [];
  return currentPath.value.split('/').filter(Boolean);
});

const columns = [
  { colKey: 'row-select', type: 'single', width: 40 },
  { colKey: 'name', title: t('common.name'),
    cell: (h: any, { row }: any) => {
      const icon = row.is_dir ? 'folder' : 'file';
      const color = row.is_dir ? '#e37318' : '#666';
      return h('div', { style: { display: 'flex', alignItems: 'center', gap: '6px' } }, [
        h('t-icon', { name: icon, size: '16px', style: { color } }),
        h('span', row.name),
      ]);
    }
  },
  { colKey: 'size', title: t('sftp.size'), width: 100,
    cell: (h: any, { row }: any) => row.is_dir ? '-' : formatSize(row.size)
  },
  { colKey: 'permissions', title: t('sftp.permissions'), width: 110 },
  { colKey: 'modified_at', title: t('sftp.modifiedAt'), width: 170,
    cell: (h: any, { row }: any) => row.modified_at ? new Date(row.modified_at).toLocaleString() : '-'
  },
];

function formatSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return (bytes / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0) + ' ' + units[i];
}

async function loadHosts() {
  try {
    const res: any = await hostApi.list({ limit: 100 });
    const items = Array.isArray(res) ? res : (res.items || []);
    hostOptions.value = items.map((h: any) => ({
      label: `${h.name} (${h.ip_address})`,
      value: h.id,
    }));
  } catch (e) { /* handled */ }
}

async function onHostChange() {
  navigateTo('/');
}

async function refreshList() {
  if (!selectedHostId.value) return;
  loading.value = true;
  try {
    const res: any = await sftpApi.listFiles(selectedHostId.value, currentPath.value);
    files.value = res.files || [];
    selectedRowKeys.value = [];
  } catch (e: any) {
    files.value = [];
  } finally {
    loading.value = false;
  }
}

async function navigateTo(path: string) {
  currentPath.value = path;
  await refreshList();
}

function onDblClick({ row }: any) {
  if (row.is_dir) {
    navigateTo(row.path);
  }
}

function onSelectChange(value: string[]) {
  selectedRowKeys.value = value;
}

// Cut / Copy
function onCut() {
  if (!selectedFile.value) return;
  clipboard.sourcePath = selectedFile.value.path;
  clipboard.name = selectedFile.value.name;
  clipboard.isCut = true;
  MessagePlugin.info(t('sftp.cutTip'));
}

function onCopy() {
  if (!selectedFile.value) return;
  clipboard.sourcePath = selectedFile.value.path;
  clipboard.name = selectedFile.value.name;
  clipboard.isCut = false;
  MessagePlugin.info(t('sftp.copyTip'));
}

async function onPaste() {
  if (!clipboard.sourcePath || !selectedHostId.value) return;
  loading.value = true;
  try {
    if (clipboard.isCut) {
      await sftpApi.moveFile(selectedHostId.value, clipboard.sourcePath, currentPath.value);
    } else {
      await sftpApi.copyFile(selectedHostId.value, clipboard.sourcePath, currentPath.value);
    }
    clearClipboard();
    await refreshList();
    MessagePlugin.success(t('common.success'));
  } catch (e: any) {
    MessagePlugin.error(e.response?.data?.detail || t('common.failed'));
  } finally {
    loading.value = false;
  }
}

function clearClipboard() {
  clipboard.sourcePath = '';
  clipboard.name = '';
  clipboard.isCut = false;
}

// Upload
function triggerUpload() {
  uploadInput.value?.click();
}

async function onUpload(e: Event) {
  const input = e.target as HTMLInputElement;
  const fileList = input.files;
  if (!fileList || fileList.length === 0 || !selectedHostId.value) return;

  uploading.value = true;
  uploadProgress.value = 0;

  try {
    const form = new FormData();
    for (let i = 0; i < fileList.length; i++) {
      form.append('files', fileList[i]);
    }
    uploadStatus.value = t('sftp.uploading');
    
    await sftpApi.uploadFile(selectedHostId.value, currentPath.value, form);
    uploadProgress.value = 100;
    uploadStatus.value = t('common.success');
    await refreshList();
    MessagePlugin.success(t('common.success'));
  } catch (e: any) {
    MessagePlugin.error(e.response?.data?.detail || t('common.failed'));
  } finally {
    uploading.value = false;
    input.value = '';
  }
}

// Download
async function onDownload() {
  if (!selectedFile.value || !selectedHostId.value) return;
  try {
    const res: any = await sftpApi.downloadFile(selectedHostId.value, selectedFile.value.path);
    const url = window.URL.createObjectURL(new Blob([res]));
    const a = document.createElement('a');
    a.href = url;
    a.download = selectedFile.value.name;
    a.click();
    window.URL.revokeObjectURL(url);
  } catch (e: any) {
    MessagePlugin.error(e.response?.data?.detail || t('common.failed'));
  }
}

// Delete
function onDeleteFile() {
  if (!selectedFile.value || !selectedHostId.value) return;
  const confirmDialog = DialogPlugin.confirm({
    header: t('common.delete'),
    body: t('sftp.confirmDelete', { name: selectedFile.value.name }),
    theme: 'danger',
    onConfirm: async () => {
      loading.value = true;
      try {
        await sftpApi.deleteFile(selectedHostId.value!, selectedFile.value!.path);
        selectedRowKeys.value = [];
        await refreshList();
        MessagePlugin.success(t('common.success'));
      } catch (e: any) {
        MessagePlugin.error(e.response?.data?.detail || t('common.failed'));
      } finally {
        loading.value = false;
      }
      confirmDialog.destroy();
    },
    onClose: () => confirmDialog.destroy(),
  });
}

// Mkdir
async function onMkdir() {
  if (!mkdirForm.name || !selectedHostId.value) return;
  mkdirLoading.value = true;
  try {
    await sftpApi.mkdir(selectedHostId.value, currentPath.value, mkdirForm.name);
    showMkdir.value = false;
    mkdirForm.name = '';
    await refreshList();
    MessagePlugin.success(t('common.success'));
  } catch (e: any) {
    MessagePlugin.error(e.response?.data?.detail || t('common.failed'));
  } finally {
    mkdirLoading.value = false;
  }
}

// Rename
async function onRename() {
  if (!renameForm.new_name || !selectedFile.value || !selectedHostId.value) return;
  renameLoading.value = true;
  try {
    await sftpApi.renameFile(selectedHostId.value, selectedFile.value.path, renameForm.new_name);
    showRename.value = false;
    renameForm.new_name = '';
    selectedRowKeys.value = [];
    await refreshList();
    MessagePlugin.success(t('common.success'));
  } catch (e: any) {
    MessagePlugin.error(e.response?.data?.detail || t('common.failed'));
  } finally {
    renameLoading.value = false;
  }
}

onMounted(() => {
  loadHosts();
});
</script>

<style scoped>
.sftp-page {
  height: 100%;
}

.sftp-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 400px;
}

.sftp-nav {
  margin-bottom: 12px;
  padding: 8px 12px;
  background: var(--td-bg-color-container);
  border-radius: 6px;
}

.sftp-toolbar {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}

.sftp-nav :deep(.t-breadcrumb__item) {
  cursor: pointer;
}
</style>
