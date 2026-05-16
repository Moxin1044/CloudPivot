<template>
  <div class="host-detail">
    <t-card :bordered="false">
      <template #title>
        <t-button variant="text" @click="$router.back()">
          <template #icon><t-icon name="chevron-left" /></template>
          {{ $t('common.back') }}
        </t-button>
        {{ host.name }}
      </template>
      <t-descriptions :data="descData" :column="2" bordered />
      <div style="margin-top: 16px; display: flex; gap: 8px;">
        <t-button theme="primary" @click="onTest">{{ $t('host.testConnectivity') }}</t-button>
        <t-button variant="outline" @click="$router.push({ path: '/terminal', query: { hostId: host.id } })">
          {{ $t('terminal.connect') }}
        </t-button>
      </div>
    </t-card>

    <t-card :bordered="false" style="margin-top: 16px" :header="$t('host.monitoring')">
      <div ref="chartRef" style="height: 300px"></div>
    </t-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { MessagePlugin } from 'tdesign-vue-next';
import { useI18n } from 'vue-i18n';
import { hostApi, monitorApi } from '@/api';

const route = useRoute();
const { t } = useI18n();
const hostId = Number(route.params.id);
const host = ref<any>({});
const chartRef = ref<HTMLElement>();
const descData = ref<any[]>([]);

async function loadHost() {
  try {
    const res: any = await hostApi.get(hostId);
    host.value = res;
    descData.value = [
      { label: t('common.name'), value: res.name },
      { label: t('host.ip'), value: res.ip_address },
      { label: t('host.port'), value: res.port },
      { label: t('host.username'), value: res.username },
      { label: t('host.authType'), value: res.auth_type },
      { label: t('common.status'), value: res.status },
      { label: t('host.os'), value: res.os_info || '-' },
      { label: t('host.lastConnected'), value: res.last_connected_at || '-' },
    ];
  } catch (e) { /* handled */ }
}

async function onTest() {
  try {
    const res: any = await hostApi.testConnectivity(hostId);
    if (res.success) MessagePlugin.success(`${t('host.connectSuccess')} (${res.latency_ms?.toFixed(0)}ms)`);
    else MessagePlugin.error(`${t('host.connectFailed')}: ${res.message}`);
    loadHost();
  } catch (e) { /* handled */ }
}

onMounted(() => loadHost());
</script>
