<template>
  <div class="terminal-page">
    <t-card :bordered="false" :title="$t('terminal.title')">
      <template #actions>
        <div style="display: flex; gap: 8px;">
          <t-select
            v-model="selectedHostId"
            :options="hostOptions"
            :placeholder="$t('terminal.selectHost')"
            style="width: 250px"
            filterable
          />
          <t-button theme="primary" :disabled="!selectedHostId" @click="connect">
            {{ $t('terminal.connect') }}
          </t-button>
          <t-button variant="outline" @click="addTab">
            <template #icon><t-icon name="add" /></template>
            {{ $t('terminal.newTab') }}
          </t-button>
        </div>
      </template>

      <t-tabs v-model="activeTab" :theme="'card'" @remove="onRemoveTab" :draggable="true">
        <t-tab-panel
          v-for="tab in tabs"
          :key="tab.id"
          :value="tab.id"
          :label="tab.label"
          :removable="true"
        >
          <div class="terminal-container">
            <div :ref="el => setTerminalRef(tab.id, el)" class="terminal-instance"></div>
            <div v-if="!tab.connected" class="terminal-placeholder">
              <t-empty :description="$t('terminal.selectHostAndConnect')" />
            </div>
          </div>
        </t-tab-panel>
      </t-tabs>

      <div v-if="tabs.length === 0" class="terminal-placeholder">
        <t-empty :description="$t('terminal.clickNewTab')" />
      </div>
    </t-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { WebLinksAddon } from '@xterm/addon-web-links';
import '@xterm/xterm/css/xterm.css';
import { hostApi } from '@/api';

const { t } = useI18n();
const route = useRoute();
const selectedHostId = ref<number | undefined>(undefined);
const hostOptions = ref<any[]>([]);
const activeTab = ref('');
const tabs = ref<any[]>([]);
const terminalRefs = ref<Record<string, any>>({});
const terminals = ref<Record<string, Terminal>>({});
const fitAddons = ref<Record<string, FitAddon>>({});
const sockets = ref<Record<string, WebSocket>>({});

function setTerminalRef(tabId: string, el: any) {
  if (el) terminalRefs.value[tabId] = el;
}

async function loadHosts() {
  try {
    const res: any = await hostApi.list({ limit: 100 });
    hostOptions.value = (Array.isArray(res) ? res : []).map((h: any) => ({
      label: `${h.name} (${h.ip_address})`,
      value: h.id,
    }));
    if (route.query.hostId) {
      selectedHostId.value = Number(route.query.hostId);
    }
  } catch (e) { /* handled */ }
}

function addTab() {
  const id = `tab-${Date.now()}`;
  tabs.value.push({ id, label: t('terminal.newTerminal'), hostId: null, connected: false });
  activeTab.value = id;

  nextTick(() => {
    initTerminal(id);
  });
}

function initTerminal(tabId: string) {
  const el = terminalRefs.value[tabId];
  if (!el) return;

  const term = new Terminal({
    cursorBlink: true,
    fontSize: 14,
    fontFamily: 'Menlo, Monaco, "Courier New", monospace',
    theme: {
      background: '#1e1e2e',
      foreground: '#cdd6f4',
    },
  });

  const fitAddon = new FitAddon();
  term.loadAddon(fitAddon);
  term.loadAddon(new WebLinksAddon());

  term.open(el);
  fitAddon.fit();

  terminals.value[tabId] = term;
  fitAddons.value[tabId] = fitAddon;

  term.onData((data) => {
    const ws = sockets.value[tabId];
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'input', data }));
    }
  });

  term.onResize(({ cols, rows }) => {
    const ws = sockets.value[tabId];
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'resize', cols, rows }));
    }
  });
}

function connect() {
  if (!selectedHostId.value) return;
  const tabId = activeTab.value;
  if (!tabId) {
    addTab();
    return;
  }

  const tab = tabs.value.find(t => t.id === tabId);
  if (!tab) return;

  const token = localStorage.getItem('token');
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsBase = `${wsProtocol}//${window.location.host}`;
  const wsUrl = `${wsBase}/api/v1/ws/ssh/${selectedHostId.value}?token=${token}`;

  const ws = new WebSocket(wsUrl, ['binary']);
  ws.binaryType = 'arraybuffer';

  ws.onopen = () => {
    tab.connected = true;
    tab.hostId = selectedHostId.value;
    const host = hostOptions.value.find(h => h.value === selectedHostId.value);
    tab.label = host?.label || 'Terminal';
  };

  ws.onmessage = (event) => {
    const term = terminals.value[tabId];
    if (!term) return;

    if (typeof event.data === 'string') {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'connected') {
          term.write(`\r\n\x1b[32mConnected to ${msg.host} as ${msg.username}\x1b[0m\r\n`);
        } else if (msg.type === 'error') {
          term.write(`\r\n\x1b[31m${msg.message}\x1b[0m\r\n`);
        } else if (msg.type === 'blocked') {
          term.write(`\r\n\x1b[31m[BLOCKED] ${msg.command} (${msg.risk})\x1b[0m\r\n`);
        }
      } catch {
        term.write(event.data);
      }
    } else if (event.data instanceof ArrayBuffer) {
      const decoder = new TextDecoder();
      term.write(decoder.decode(event.data));
    }
  };

  ws.onclose = () => {
    const term = terminals.value[tabId];
    if (term) term.write('\r\n\x1b[33mDisconnected\x1b[0m\r\n');
    tab.connected = false;
  };

  ws.onerror = () => {
    const term = terminals.value[tabId];
    if (term) term.write('\r\n\x1b[31mConnection error\x1b[0m\r\n');
  };

  sockets.value[tabId] = ws;
}

function onRemoveTab({ value }: any) {
  const ws = sockets.value[value];
  if (ws) ws.close();
  const term = terminals.value[value];
  if (term) term.dispose();
  delete sockets.value[value];
  delete terminals.value[value];
  delete fitAddons.value[value];
  tabs.value = tabs.value.filter(t => t.id !== value);
}

onMounted(() => {
  loadHosts();
  addTab();
});

onBeforeUnmount(() => {
  Object.values(sockets.value).forEach(ws => ws.close());
  Object.values(terminals.value).forEach(term => term.dispose());
});
</script>

<style scoped>
.terminal-container {
  position: relative;
  height: 500px;
  background: #1e1e2e;
  border-radius: 8px;
  overflow: hidden;
}
.terminal-instance {
  height: 100%;
  padding: 8px;
}
.terminal-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 500px;
  background: #1e1e2e;
  border-radius: 8px;
}
</style>
