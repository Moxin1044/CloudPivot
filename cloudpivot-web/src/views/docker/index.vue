<template>
  <div class="docker-page">
    <t-tabs v-model="activeTab">
      <t-tab-panel value="containers" :label="$t('docker.containers')">
        <t-card :bordered="false">
          <template #actions>
            <t-radio-group v-model="showAll" variant="default-filled" @change="loadContainers">
              <t-radio-button :value="false">运行中</t-radio-button>
              <t-radio-button :value="true">全部</t-radio-button>
            </t-radio-group>
            <t-button variant="outline" @click="loadContainers">
              <template #icon><t-icon name="refresh" /></template>
            </t-button>
          </template>
          <t-table :data="containers" :columns="containerColumns" :loading="loading" row-key="id" />
        </t-card>
      </t-tab-panel>
      <t-tab-panel value="images" :label="$t('docker.images')">
        <t-card :bordered="false">
          <template #actions>
            <t-button theme="primary" @click="showPull = true">{{ $t('docker.pull') }}</t-button>
            <t-button variant="outline" @click="loadImages">
              <template #icon><t-icon name="refresh" /></template>
            </t-button>
          </template>
          <t-table :data="images" :columns="imageColumns" :loading="imgLoading" row-key="id" />
        </t-card>
      </t-tab-panel>
      <t-tab-panel value="hosts" :label="$t('docker.host')">
        <t-card :bordered="false">
          <template #actions>
            <t-button theme="primary" @click="showHostCreate = true">{{ $t('common.create') }}</t-button>
          </template>
          <t-table :data="dockerHosts" :columns="hostColumns" :loading="hostLoading" row-key="id" />
        </t-card>
      </t-tab-panel>
    </t-tabs>

    <!-- Container Action Dialogs -->
    <t-dialog v-model:visible="showLogs" header="容器日志" :footer="false" width="700px">
      <div class="log-viewer">
        <pre>{{ containerLogs }}</pre>
      </div>
    </t-dialog>

    <t-dialog v-model:visible="showPull" header="拉取镜像" @confirm="onPullImage">
      <t-form :data="pullForm" label-align="top">
        <t-form-item label="镜像仓库"><t-input v-model="pullForm.repository" placeholder="e.g. nginx" /></t-form-item>
        <t-form-item label="标签"><t-input v-model="pullForm.tag" placeholder="latest" /></t-form-item>
      </t-form>
    </t-dialog>

    <t-dialog v-model:visible="showHostCreate" header="添加Docker主机" @confirm="onCreateHost">
      <t-form :data="hostForm" label-align="top">
        <t-form-item label="名称"><t-input v-model="hostForm.name" /></t-form-item>
        <t-form-item label="地址"><t-input v-model="hostForm.host" placeholder="unix:///var/run/docker.sock" /></t-form-item>
      </t-form>
    </t-dialog>

    <t-dialog v-model:visible="showExec" header="执行命令" @confirm="onExec">
      <t-form :data="execForm" label-align="top">
        <t-form-item label="命令"><t-input v-model="execForm.command" /></t-form-item>
      </t-form>
    </t-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { MessagePlugin } from 'tdesign-vue-next';
import { dockerApi } from '@/api';

const activeTab = ref('containers');
const containers = ref<any[]>([]);
const images = ref<any[]>([]);
const dockerHosts = ref<any[]>([]);
const loading = ref(false);
const imgLoading = ref(false);
const hostLoading = ref(false);
const showAll = ref(false);
const showLogs = ref(false);
const showPull = ref(false);
const showHostCreate = ref(false);
const showExec = ref(false);
const containerLogs = ref('');
const execContainerId = ref('');

const pullForm = reactive({ repository: '', tag: 'latest' });
const hostForm = reactive({ name: '', host: 'unix:///var/run/docker.sock' });
const execForm = reactive({ command: '' });

const containerColumns = [
  { colKey: 'id', title: 'ID', width: 100 },
  { colKey: 'name', title: '名称', width: 150 },
  { colKey: 'image', title: '镜像', width: 200, ellipsis: true },
  { colKey: 'state', title: '状态', width: 80,
    cell: (h: any, { row }: any) => h('t-tag', { props: { theme: row.state === 'running' ? 'success' : 'default', size: 'small' } }, row.state)
  },
  { colKey: 'status', title: '详情', width: 150 },
  { colKey: 'actions', title: '操作', width: 280,
    cell: (_h: any, { row }: any) => _h('div', { style: 'display:flex;gap:4px;flex-wrap:wrap' }, [
      row.state !== 'running' ? _h('t-button', { props: { size: 'small', variant: 'text', theme: 'primary' }, on: { click: () => onStart(row.id) } }, '启动') : null,
      row.state === 'running' ? _h('t-button', { props: { size: 'small', variant: 'text', theme: 'warning' }, on: { click: () => onStop(row.id) } }, '停止') : null,
      _h('t-button', { props: { size: 'small', variant: 'text', theme: 'primary' }, on: { click: () => onRestart(row.id) } }, '重启'),
      _h('t-button', { props: { size: 'small', variant: 'text' }, on: { click: () => onViewLogs(row.id) } }, '日志'),
      _h('t-button', { props: { size: 'small', variant: 'text' }, on: { click: () => { execContainerId.value = row.id; showExec.value = true; } } }, 'Exec'),
      _h('t-button', { props: { size: 'small', variant: 'text', theme: 'danger' }, on: { click: () => onRemove(row.id) } }, '删除'),
    ].filter(Boolean))
  },
];

const imageColumns = [
  { colKey: 'id', title: 'ID', width: 100 },
  { colKey: 'repo_tags', title: '标签', ellipsis: true,
    cell: (h: any, { row }: any) => h('span', (row.repo_tags || []).join(', '))
  },
  { colKey: 'size_mb', title: '大小(MB)', width: 100 },
  { colKey: 'actions', title: '操作', width: 80,
    cell: (_h: any, { row }: any) => _h('t-button', { props: { size: 'small', variant: 'text', theme: 'danger' }, on: { click: () => onRemoveImage(row.id) } }, '删除')
  },
];

const hostColumns = [
  { colKey: 'name', title: '名称' },
  { colKey: 'host', title: '地址' },
  { colKey: 'is_active', title: '状态' },
  { colKey: 'actions', title: '操作',
    cell: (_h: any, { row }: any) => _h('t-button', { props: { variant: 'text', theme: 'danger', size: 'small' }, on: { click: () => onDeleteHost(row.id) } }, '删除')
  },
];

async function loadContainers() {
  loading.value = true;
  try { containers.value = await dockerApi.listContainers(showAll.value); } finally { loading.value = false; }
}

async function loadImages() {
  imgLoading.value = true;
  try { images.value = await dockerApi.listImages(); } finally { imgLoading.value = false; }
}

async function loadDockerHosts() {
  hostLoading.value = true;
  try { dockerHosts.value = await dockerApi.listHosts(); } finally { hostLoading.value = false; }
}

async function onStart(id: string) { await dockerApi.startContainer(id); MessagePlugin.success('已启动'); loadContainers(); }
async function onStop(id: string) { await dockerApi.stopContainer(id); MessagePlugin.success('已停止'); loadContainers(); }
async function onRestart(id: string) { await dockerApi.restartContainer(id); MessagePlugin.success('已重启'); loadContainers(); }
async function onRemove(id: string) { await dockerApi.removeContainer(id); MessagePlugin.success('已删除'); loadContainers(); }

async function onViewLogs(id: string) {
  try {
    const res: any = await dockerApi.getContainerLogs(id, 200);
    containerLogs.value = res.logs || '';
    showLogs.value = true;
  } catch (e) { /* */ }
}

async function onExec() {
  await dockerApi.execInContainer(execContainerId.value, execForm.command);
  MessagePlugin.success('命令已执行');
  showExec.value = false;
}

async function onPullImage() {
  await dockerApi.pullImage(pullForm.repository, pullForm.tag);
  MessagePlugin.success('拉取成功');
  showPull.value = false;
  loadImages();
}

async function onRemoveImage(id: string) { await dockerApi.removeImage(id); loadImages(); }
async function onCreateHost() { await dockerApi.createHost(hostForm); showHostCreate.value = false; loadDockerHosts(); }
async function onDeleteHost(id: number) { await dockerApi.deleteHost(id); loadDockerHosts(); }

onMounted(() => { loadContainers(); loadImages(); loadDockerHosts(); });
</script>

<style scoped>
.log-viewer { max-height: 500px; overflow-y: auto; background: #1e1e2e; color: #cdd6f4; padding: 16px; border-radius: 8px; }
.log-viewer pre { margin: 0; font-size: 12px; white-space: pre-wrap; word-break: break-all; }
</style>
