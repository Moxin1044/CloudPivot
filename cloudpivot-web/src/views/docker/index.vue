<template>
  <div class="docker-page">
    <t-tabs v-model="activeTab">
      <t-tab-panel value="containers" :label="$t('docker.containers')">
        <t-card :bordered="false">
          <template #actions>
            <t-radio-group v-model="showAll" variant="default-filled" @change="loadContainers">
              <t-radio-button :value="false">{{ $t('docker.runningTab') }}</t-radio-button>
              <t-radio-button :value="true">{{ $t('docker.allTab') }}</t-radio-button>
            </t-radio-group>
            <t-button variant="outline" @click="loadContainers">
              <template #icon><t-icon name="refresh" /></template>
            </t-button>
          </template>
          <t-table :data="containers" :columns="containerColumns" :loading="loading" row-key="id">
            <template #actions="{ row }">
              <t-space>
                <t-button v-if="row.state !== 'running'" variant="outline" theme="primary" size="small" @click="onStart(row.id)">{{ $t('docker.start') }}</t-button>
                <t-button v-if="row.state === 'running'" variant="outline" theme="warning" size="small" @click="onStop(row.id)">{{ $t('docker.stop') }}</t-button>
                <t-button variant="outline" theme="primary" size="small" @click="onRestart(row.id)">{{ $t('docker.restart') }}</t-button>
                <t-button variant="outline" size="small" @click="onViewLogs(row.id)">{{ $t('docker.logs') }}</t-button>
                <t-button variant="outline" size="small" @click="execContainerId = row.id; showExec = true">{{ $t('docker.exec') }}</t-button>
                <t-button variant="outline" theme="danger" size="small" @click="onRemove(row.id)">{{ $t('common.delete') }}</t-button>
              </t-space>
            </template>
          </t-table>
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
          <t-table :data="images" :columns="imageColumns" :loading="imgLoading" row-key="id">
            <template #actions="{ row }">
              <t-button variant="outline" theme="danger" size="small" @click="onRemoveImage(row.id)">{{ $t('common.delete') }}</t-button>
            </template>
          </t-table>
        </t-card>
      </t-tab-panel>
      <t-tab-panel value="hosts" :label="$t('docker.host')">
        <t-card :bordered="false">
          <template #actions>
            <t-button theme="primary" @click="showHostCreate = true">{{ $t('common.create') }}</t-button>
          </template>
          <t-table :data="dockerHosts" :columns="hostColumns" :loading="hostLoading" row-key="id">
            <template #actions="{ row }">
              <t-button variant="outline" theme="danger" size="small" @click="onDeleteHost(row.id)">{{ $t('common.delete') }}</t-button>
            </template>
          </t-table>
        </t-card>
      </t-tab-panel>
    </t-tabs>

    <!-- Container Action Dialogs -->
    <t-dialog v-model:visible="showLogs" :header="$t('docker.containerLogs')" :footer="false" width="700px">
      <div class="log-viewer">
        <pre>{{ containerLogs }}</pre>
      </div>
    </t-dialog>

    <t-dialog v-model:visible="showPull" :header="$t('docker.pullImage')" @confirm="onPullImage">
      <t-form :data="pullForm" label-align="top">
        <t-form-item :label="$t('docker.repository')"><t-input v-model="pullForm.repository" placeholder="e.g. nginx" /></t-form-item>
        <t-form-item :label="$t('docker.tag')"><t-input v-model="pullForm.tag" placeholder="latest" /></t-form-item>
      </t-form>
    </t-dialog>

    <t-dialog v-model:visible="showHostCreate" :header="$t('docker.addDockerHost')" @confirm="onCreateHost">
      <t-form :data="hostForm" label-align="top">
        <t-form-item :label="$t('common.name')"><t-input v-model="hostForm.name" /></t-form-item>
        <t-form-item :label="$t('docker.address')"><t-input v-model="hostForm.host" placeholder="unix:///var/run/docker.sock" /></t-form-item>
      </t-form>
    </t-dialog>

    <t-dialog v-model:visible="showExec" :header="$t('docker.execCommand')" @confirm="onExec">
      <t-form :data="execForm" label-align="top">
        <t-form-item :label="$t('docker.exec')"><t-input v-model="execForm.command" /></t-form-item>
      </t-form>
    </t-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { MessagePlugin } from 'tdesign-vue-next';
import { useI18n } from 'vue-i18n';
import { dockerApi } from '@/api';

const { t } = useI18n();
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
  { colKey: 'name', title: t('common.name'), width: 150 },
  { colKey: 'image', title: t('docker.image'), width: 200, ellipsis: true },
  { colKey: 'state', title: t('common.status'), width: 80,
    cell: (h: any, { row }: any) => h('t-tag', { props: { theme: row.state === 'running' ? 'success' : 'default', size: 'small' } }, row.state)
  },
  { colKey: 'status', title: t('docker.detail'), width: 150 },
  { colKey: 'actions', title: t('common.actions'), width: 340 },
];

const imageColumns = [
  { colKey: 'id', title: 'ID', width: 100 },
  { colKey: 'repo_tags', title: t('common.name'), ellipsis: true,
    cell: (h: any, { row }: any) => h('span', (row.repo_tags || []).join(', '))
  },
  { colKey: 'size_mb', title: t('docker.sizeMB'), width: 100 },
  { colKey: 'actions', title: t('common.actions'), width: 100 },
];

const hostColumns = [
  { colKey: 'name', title: t('common.name') },
  { colKey: 'host', title: t('docker.address') },
  { colKey: 'is_active', title: t('common.status') },
  { colKey: 'actions', title: t('common.actions'), width: 100 },
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

async function onStart(id: string) { await dockerApi.startContainer(id); MessagePlugin.success(t('docker.started')); loadContainers(); }
async function onStop(id: string) { await dockerApi.stopContainer(id); MessagePlugin.success(t('docker.stoppedMsg')); loadContainers(); }
async function onRestart(id: string) { await dockerApi.restartContainer(id); MessagePlugin.success(t('docker.restarted')); loadContainers(); }
async function onRemove(id: string) { await dockerApi.removeContainer(id); MessagePlugin.success(t('docker.removed')); loadContainers(); }

async function onViewLogs(id: string) {
  try {
    const res: any = await dockerApi.getContainerLogs(id, 200);
    containerLogs.value = res.logs || '';
    showLogs.value = true;
  } catch (e) { /* */ }
}

async function onExec() {
  await dockerApi.execInContainer(execContainerId.value, execForm.command);
  MessagePlugin.success(t('docker.commandExecuted'));
  showExec.value = false;
}

async function onPullImage() {
  await dockerApi.pullImage(pullForm.repository, pullForm.tag);
  MessagePlugin.success(t('docker.pullSuccess'));
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
