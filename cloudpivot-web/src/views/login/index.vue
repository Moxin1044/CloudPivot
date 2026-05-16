<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <h1>{{ $t('login.title') }}</h1>
        <p>{{ $t('login.subtitle') }}</p>
      </div>
      <t-form
        ref="formRef"
        :data="formData"
        :rules="formRules"
        label-align="top"
        @submit="onSubmit"
      >
        <t-form-item :label="$t('login.username')" name="username">
          <t-input v-model="formData.username" :placeholder="$t('login.username')" clearable>
            <template #prefix-icon><t-icon name="user" /></template>
          </t-input>
        </t-form-item>
        <t-form-item :label="$t('login.password')" name="password">
          <t-input
            v-model="formData.password"
            type="password"
            :placeholder="$t('login.password')"
            clearable
          >
            <template #prefix-icon><t-icon name="lock-on" /></template>
          </t-input>
        </t-form-item>
        <t-form-item>
          <t-button theme="primary" type="submit" block :loading="loading">
            {{ $t('login.login') }}
          </t-button>
        </t-form-item>
      </t-form>
      <div class="login-footer">
        <t-button variant="text" @click="showRegister = true">
          {{ $t('login.noAccount') }}{{ $t('login.register') }}
        </t-button>
      </div>
    </div>

    <!-- Register Dialog -->
    <t-dialog
      v-model:visible="showRegister"
      :header="$t('login.register')"
      :confirm-btn="{ loading: registerLoading }"
      @confirm="onRegister"
    >
      <t-form :data="registerData" label-align="top">
        <t-form-item :label="$t('login.username')" name="username">
          <t-input v-model="registerData.username" />
        </t-form-item>
        <t-form-item :label="$t('login.email')" name="email">
          <t-input v-model="registerData.email" />
        </t-form-item>
        <t-form-item :label="$t('login.password')" name="password">
          <t-input v-model="registerData.password" type="password" />
        </t-form-item>
      </t-form>
    </t-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { MessagePlugin } from 'tdesign-vue-next';
import { authApi } from '@/api';
import { useUserStore } from '@/stores/app';

const { t } = useI18n();
const router = useRouter();
const userStore = useUserStore();
const loading = ref(false);
const showRegister = ref(false);
const registerLoading = ref(false);

const formData = reactive({ username: '', password: '' });
const registerData = reactive({ username: '', email: '', password: '' });

const formRules = {
  username: [{ required: true, message: t('login.enterUsername') }],
  password: [{ required: true, message: t('login.enterPassword') }],
};

async function onSubmit({ validateResult }: any) {
  if (validateResult !== true) return;
  loading.value = true;
  try {
    const res: any = await authApi.login(formData);
    userStore.setTokens(res.access_token, res.refresh_token);
    const userInfo = await authApi.getMe();
    userStore.setUser(userInfo);
    MessagePlugin.success(t('login.loginSuccess'));
    router.push('/dashboard');
  } catch (e: any) {
    // error handled by interceptor
  } finally {
    loading.value = false;
  }
}

async function onRegister() {
  registerLoading.value = true;
  try {
    await authApi.register(registerData);
    MessagePlugin.success(t('login.registerSuccess'));
    showRegister.value = false;
  } catch (e: any) {
    // error handled by interceptor
  } finally {
    registerLoading.value = false;
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.login-card {
  width: 400px;
  padding: 48px 40px;
  background: var(--td-bg-color-container);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
}
.login-header {
  text-align: center;
  margin-bottom: 32px;
}
.login-header h1 {
  font-size: 28px;
  font-weight: 700;
  margin: 0 0 8px;
  color: var(--td-brand-color);
}
.login-header p {
  color: var(--td-text-color-secondary);
  margin: 0;
}
.login-footer {
  text-align: center;
  margin-top: 16px;
}
</style>
