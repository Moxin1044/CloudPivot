<template>
  <div class="dashboard">
    <t-row :gutter="[16, 16]">
      <t-col :span="3" v-for="item in statCards" :key="item.key">
        <t-card class="stat-card" :bordered="false">
          <div class="stat-content">
            <div class="stat-info">
              <div class="stat-label">{{ $t(`dashboard.${item.key}`) }}</div>
              <div class="stat-value">{{ item.value }}</div>
            </div>
            <div class="stat-icon" :style="{ background: item.color }">
              <t-icon :name="item.icon" size="28px" style="color: #fff" />
            </div>
          </div>
        </t-card>
      </t-col>
    </t-row>

    <t-row :gutter="[16, 16]" style="margin-top: 16px">
      <t-col :span="8">
        <t-card :title="$t('dashboard.resourceUsage')" :bordered="false">
          <div ref="chartRef" style="height: 300px"></div>
        </t-card>
      </t-col>
      <t-col :span="4">
        <t-card :title="$t('dashboard.recentAlerts')" :bordered="false">
          <t-list :split="true">
            <t-list-item v-for="alert in data.recentAlerts" :key="alert.id">
              <t-list-item-meta
                :title="alert.title"
                :description="formatTime(alert.created_at)"
              />
              <template #action>
                <t-tag :theme="severityTheme(alert.severity)" size="small">
                  {{ alert.severity }}
                </t-tag>
              </template>
            </t-list-item>
          </t-list>
          <t-empty v-if="!data.recentAlerts?.length" />
        </t-card>
      </t-col>
    </t-row>

    <t-row :gutter="[16, 16]" style="margin-top: 16px">
      <t-col :span="12">
        <t-card :title="$t('dashboard.recentAudits')" :bordered="false">
          <t-table
            :data="data.recentAudits"
            :columns="auditColumns"
            size="small"
            :pagination="false"
          />
        </t-card>
      </t-col>
    </t-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { dashboardApi } from '@/api';
import dayjs from 'dayjs';

const data = ref<any>({ overview: {}, resourceUsage: [], recentAudits: [], recentAlerts: [] });
const chartRef = ref<HTMLElement>();

const statCards = computed(() => {
  const o = data.value.overview || {};
  return [
    { key: 'totalHosts', value: o.total_hosts || 0, icon: 'server', color: '#0052d9' },
    { key: 'onlineHosts', value: o.online_hosts || 0, icon: 'check-circle', color: '#00a870' },
    { key: 'activeSessions', value: o.active_sessions || 0, icon: 'root-list', color: '#e37318' },
    { key: 'totalContainers', value: o.total_containers || 0, icon: 'control-platform', color: '#8c5fe0' },
    { key: 'runningContainers', value: o.running_containers || 0, icon: 'play-circle', color: '#0594fa' },
    { key: 'totalUsers', value: o.total_users || 0, icon: 'usergroup', color: '#d54941' },
    { key: 'activeAlerts', value: o.active_alerts || 0, icon: 'error-circle', color: '#e34d59' },
    { key: 'riskCommandsToday', value: o.risk_commands_today || 0, icon: 'close-circle', color: '#c9353f' },
  ];
});

const auditColumns = [
  { colKey: 'username', title: 'User', width: 120 },
  { colKey: 'host_name', title: 'Host', width: 150 },
  { colKey: 'command', title: 'Command', ellipsis: true },
  { colKey: 'risk_level', title: 'Risk', width: 80,
    cell: (h: any, { row }: any) => h('t-tag', { props: { theme: row.risk_level === 'danger' ? 'danger' : row.risk_level === 'warning' ? 'warning' : 'default', size: 'small' } }, row.risk_level)
  },
  { colKey: 'executed_at', title: 'Time', width: 180, cell: (h: any, { row }: any) => formatTime(row.executed_at) },
];

function formatTime(t: string) {
  return t ? dayjs(t).format('YYYY-MM-DD HH:mm:ss') : '-';
}

function severityTheme(s: string) {
  return s === 'critical' ? 'danger' : s === 'warning' ? 'warning' : 'default';
}

async function loadData() {
  try {
    data.value = await dashboardApi.getOverview();
  } catch (e) {
    // handled
  }
}

onMounted(() => {
  loadData();
});
</script>

<style scoped>
.stat-card { cursor: pointer; transition: transform 0.2s; }
.stat-card:hover { transform: translateY(-2px); }
.stat-content { display: flex; justify-content: space-between; align-items: center; }
.stat-label { color: var(--td-text-color-secondary); font-size: 14px; }
.stat-value { font-size: 28px; font-weight: 700; margin-top: 8px; }
.stat-icon { width: 56px; height: 56px; border-radius: 12px; display: flex; align-items: center; justify-content: center; }
</style>
