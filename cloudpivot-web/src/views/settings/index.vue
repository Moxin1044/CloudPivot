<template>
  <div class="settings-page">
    <t-row :gutter="[16, 16]">
      <t-col :span="6">
        <t-card :title="$t('settings.profile')" :bordered="false">
          <t-form :data="profileForm" label-align="top">
            <t-form-item label="Username">
              <t-input :value="userStore.userInfo?.username" disabled />
            </t-form-item>
            <t-form-item label="Email">
              <t-input v-model="profileForm.email" />
            </t-form-item>
            <t-form-item :label="$t('settings.theme')">
              <t-radio-group :value="appStore.theme" @change="onThemeChange">
                <t-radio-button value="light">{{ $t('settings.lightMode') }}</t-radio-button>
                <t-radio-button value="dark">{{ $t('settings.darkMode') }}</t-radio-button>
              </t-radio-group>
            </t-form-item>
            <t-form-item :label="$t('settings.language')">
              <t-radio-group :value="appStore.locale" @change="onLocaleChange">
                <t-radio-button value="zh-CN">中文</t-radio-button>
                <t-radio-button value="en">English</t-radio-button>
              </t-radio-group>
            </t-form-item>
            <t-form-item>
              <t-button theme="primary" @click="onSaveProfile" :loading="profileLoading">
                {{ $t('common.save') }}
              </t-button>
            </t-form-item>
          </t-form>
        </t-card>
      </t-col>
      <t-col :span="6">
        <t-card :title="$t('settings.security')" :bordered="false">
          <t-form :data="pwdForm" label-align="top" @submit="onChangePassword">
            <t-form-item :label="$t('settings.oldPassword')">
              <t-input v-model="pwdForm.old_password" type="password" />
            </t-form-item>
            <t-form-item :label="$t('settings.newPassword')">
              <t-input v-model="pwdForm.new_password" type="password" />
            </t-form-item>
            <t-form-item>
              <t-button theme="primary" type="submit" :loading="pwdLoading">
                {{ $t('settings.changePassword') }}
              </t-button>
            </t-form-item>
          </t-form>
        </t-card>
      </t-col>
    </t-row>

    <t-row :gutter="[16, 16]" style="margin-top: 16px">
      <t-col :span="12">
        <t-card :title="$t('settings.notifications')" :bordered="false">
          <template #actions>
            <t-button theme="primary" @click="onSaveNotifications" :loading="notifLoading">
              {{ $t('common.save') }}
            </t-button>
          </template>
          <t-form :data="notifForm" label-align="top" :label-width="120">
            <t-row :gutter="[24, 16]">
              <t-col :span="6">
                <t-form-item label="通知邮箱" name="notification_email">
                  <t-input v-model="notifForm.notification_email" placeholder="your@email.com" />
                  <div class="form-tip">接收告警通知的邮箱</div>
                </t-form-item>
              </t-col>
              <t-col :span="6">
                <t-form-item label="飞书 Webhook" name="feishu_webhook">
                  <t-input v-model="notifForm.feishu_webhook" placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..." />
                  <div class="form-tip">飞书群机器人地址</div>
                </t-form-item>
              </t-col>
            </t-row>
            <t-row :gutter="[24, 16]">
              <t-col :span="6">
                <t-form-item label="钉钉 Webhook" name="dingtalk_webhook">
                  <t-input v-model="notifForm.dingtalk_webhook" placeholder="https://oapi.dingtalk.com/robot/send?access_token=..." />
                  <div class="form-tip">钉钉群机器人地址</div>
                </t-form-item>
              </t-col>
              <t-col :span="6">
                <t-form-item label="通知渠道" name="notify_channels">
                  <t-checkbox-group v-model="notifChannels">
                    <t-checkbox value="email">邮箱</t-checkbox>
                    <t-checkbox value="feishu">飞书</t-checkbox>
                    <t-checkbox value="dingtalk">钉钉</t-checkbox>
                  </t-checkbox-group>
                  <div class="form-tip">勾选后，告警将通过对应渠道发送到您配置的地址</div>
                </t-form-item>
              </t-col>
            </t-row>
          </t-form>
        </t-card>
      </t-col>
    </t-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { MessagePlugin } from 'tdesign-vue-next';
import { useAppStore, useUserStore } from '@/stores/app';
import { authApi } from '@/api';
import { useI18n } from 'vue-i18n';

const appStore = useAppStore();
const userStore = useUserStore();
const { locale } = useI18n();
const pwdLoading = ref(false);
const profileLoading = ref(false);
const notifLoading = ref(false);

const profileForm = reactive({ email: '', display_name: '' });
const pwdForm = reactive({ old_password: '', new_password: '' });
const notifForm = reactive({
  notification_email: '',
  feishu_webhook: '',
  dingtalk_webhook: '',
});
const notifChannels = ref<string[]>([]);

function onThemeChange() {
  appStore.toggleTheme();
}

function onLocaleChange(val: any) {
  const lang = val as 'zh-CN' | 'en';
  appStore.setLocale(lang);
  locale.value = lang;
}

function loadUserData() {
  const info = userStore.userInfo;
  if (info) {
    profileForm.email = info.email || '';
    profileForm.display_name = info.display_name || '';
    notifForm.notification_email = info.notification_email || '';
    notifForm.feishu_webhook = info.feishu_webhook || '';
    notifForm.dingtalk_webhook = info.dingtalk_webhook || '';
    notifChannels.value = info.notify_channels
      ? info.notify_channels.split(',').filter(Boolean)
      : [];
  }
}

async function onSaveProfile() {
  profileLoading.value = true;
  try {
    const res: any = await authApi.updateMe({
      email: profileForm.email,
      display_name: profileForm.display_name,
    });
    userStore.setUser(res);
    MessagePlugin.success('保存成功');
  } catch (e) { /* handled */ }
  finally { profileLoading.value = false; }
}

async function onChangePassword({ validateResult }: any) {
  if (validateResult !== true) return;
  pwdLoading.value = true;
  try {
    await authApi.changePassword(pwdForm);
    MessagePlugin.success('密码修改成功');
    pwdForm.old_password = '';
    pwdForm.new_password = '';
  } catch (e) { /* handled */ }
  finally { pwdLoading.value = false; }
}

async function onSaveNotifications() {
  notifLoading.value = true;
  try {
    const res: any = await authApi.updateNotifications({
      notification_email: notifForm.notification_email || null,
      feishu_webhook: notifForm.feishu_webhook || null,
      dingtalk_webhook: notifForm.dingtalk_webhook || null,
      notify_channels: notifChannels.value.join(',') || null,
    });
    userStore.setUser(res);
    MessagePlugin.success('通知配置保存成功');
  } catch (e) { /* handled */ }
  finally { notifLoading.value = false; }
}

onMounted(() => {
  loadUserData();
});
</script>

<style scoped>
.form-tip {
  font-size: 12px;
  color: var(--td-text-color-placeholder);
  margin-top: 4px;
}
</style>
