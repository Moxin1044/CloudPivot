<template>
  <div class="login-page">
    <!-- Left brand panel -->
    <div class="login-brand">
      <div class="brand-content">
        <div class="brand-logo">
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
            <rect width="48" height="48" rx="12" fill="var(--td-brand-color)" />
            <path
              d="M14 32c0-5.523 4.477-10 10-10s10 4.477 10 10"
              stroke="#fff" stroke-width="3" stroke-linecap="round"
            />
            <circle cx="24" cy="17" r="5" stroke="#fff" stroke-width="3" />
          </svg>
        </div>
        <h1 class="brand-title">{{ $t('login.title') }}</h1>
        <p class="brand-subtitle">{{ $t('login.subtitle') }}</p>
        <div class="brand-features">
          <div class="feature-item">
            <t-icon name="secured" size="20px" />
            <span>{{ $t('login.featureSecure') }}</span>
          </div>
          <div class="feature-item">
            <t-icon name="control-platform" size="20px" />
            <span>{{ $t('login.featureControl') }}</span>
          </div>
          <div class="feature-item">
            <t-icon name="chart-analytics" size="20px" />
            <span>{{ $t('login.featureAudit') }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Right form panel -->
    <div class="login-form-panel">
      <div class="form-wrapper">
        <div class="form-header">
          <h2>{{ $t('login.welcome') }}</h2>
          <p>{{ $t('login.welcomeDesc') }}</p>
        </div>

        <t-form
          ref="formRef"
          :data="formData"
          :rules="formRules"
          @submit="onSubmit"
        >
          <t-form-item name="username">
            <t-input
              v-model="formData.username"
              size="large"
              :placeholder="$t('login.username')"
              clearable
            >
              <template #prefix-icon><t-icon name="user" /></template>
            </t-input>
          </t-form-item>

          <t-form-item name="password">
            <t-input
              v-model="formData.password"
              type="password"
              size="large"
              :placeholder="$t('login.password')"
              clearable
              @keyup.enter="onSubmit"
            >
              <template #prefix-icon><t-icon name="lock-on" /></template>
            </t-input>
          </t-form-item>

          <!-- Captcha -->
          <t-form-item name="captchaCode">
            <div class="captcha-row">
              <t-input
                v-model="formData.captchaCode"
                size="large"
                :placeholder="$t('login.captcha')"
                style="flex: 1"
              >
                <template #prefix-icon><t-icon name="verify" /></template>
              </t-input>
              <img
                v-if="captchaImage"
                :src="captchaImage"
                class="captcha-img"
                @click="refreshCaptcha"
                :title="$t('login.refreshCaptcha')"
              />
              <div v-else class="captcha-loading" @click="refreshCaptcha">
                <t-icon name="refresh" />
              </div>
            </div>
          </t-form-item>

          <t-form-item>
            <t-button
              theme="primary"
              type="submit"
              block
              size="large"
              :loading="loading"
            >
              {{ $t('login.login') }}
            </t-button>
          </t-form-item>
        </t-form>

        <div class="form-footer">
          <t-button v-if="allowRegister" variant="text" @click="showRegister = true">
            {{ $t('login.noAccount') }}{{ $t('login.register') }}
          </t-button>
        </div>
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
import { ref, reactive, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { MessagePlugin } from 'tdesign-vue-next';
import { authApi, siteConfigApi } from '@/api';
import { useUserStore } from '@/stores/app';

const { t } = useI18n();
const router = useRouter();
const userStore = useUserStore();
const loading = ref(false);
const showRegister = ref(false);
const registerLoading = ref(false);
const allowRegister = ref(true);
const formRef = ref();

const formData = reactive({
  username: '',
  password: '',
  captchaId: '',
  captchaCode: '',
});
const registerData = reactive({ username: '', email: '', password: '' });

const captchaImage = ref('');
const captchaId = ref('');

const formRules = {
  username: [{ required: true, message: t('login.enterUsername'), trigger: 'change' }],
  password: [{ required: true, message: t('login.enterPassword'), trigger: 'change' }],
  captchaCode: [{ required: true, message: t('login.enterCaptcha'), trigger: 'change' }],
};

async function refreshCaptcha() {
  try {
    const res: any = await authApi.getCaptcha();
    captchaImage.value = res.captcha_image;
    captchaId.value = res.captcha_id;
    formData.captchaId = res.captcha_id;
    formData.captchaCode = '';
  } catch {
    // captcha load failed
  }
}

async function onSubmit({ validateResult }: any) {
  if (validateResult !== true) return;
  loading.value = true;
  try {
    const loginData = {
      username: formData.username,
      password: formData.password,
      captcha_id: captchaId.value,
      captcha_code: formData.captchaCode,
    };
    const res: any = await authApi.login(loginData);
    userStore.setTokens(res.access_token, res.refresh_token);
    const userInfo = await authApi.getMe();
    userStore.setUser(userInfo);
    localStorage.setItem('userInfo', JSON.stringify(userInfo));
    MessagePlugin.success(t('login.loginSuccess'));
    router.push('/dashboard');
  } catch (e: any) {
    refreshCaptcha();
    formData.captchaCode = '';
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

async function loadRegistrationStatus() {
  try {
    const res: any = await siteConfigApi.getRegistrationStatus();
    allowRegister.value = res.allow_register !== false;
  } catch {
    allowRegister.value = true;
  }
}

onMounted(() => {
  refreshCaptcha();
  loadRegistrationStatus();
});
</script>

<style scoped>
.login-page {
  display: flex;
  min-height: 100vh;
  background: var(--td-bg-color-page);
}

/* Left brand panel */
.login-brand {
  flex: 0 0 480px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--td-brand-color) 0%, var(--td-brand-color-7) 50%, var(--td-brand-color-6) 100%);
  padding: 48px;
}

.brand-content {
  color: #fff;
  max-width: 360px;
}

.brand-logo {
  margin-bottom: 24px;
}

.brand-title {
  font-size: 32px;
  font-weight: 700;
  margin: 0 0 8px 0;
}

.brand-subtitle {
  font-size: 16px;
  opacity: 0.85;
  margin: 0 0 40px 0;
  line-height: 1.5;
}

.brand-features {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
  opacity: 0.9;
}

/* Right form panel */
.login-form-panel {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px;
}

.form-wrapper {
  width: 400px;
  max-width: 100%;
}

.form-header {
  margin-bottom: 32px;
  text-align: center;
}

.form-header h2 {
  font-size: 24px;
  font-weight: 600;
  color: var(--td-text-color-primary);
  margin: 0 0 8px 0;
}

.form-header p {
  font-size: 14px;
  color: var(--td-text-color-secondary);
  margin: 0;
}

/* Captcha */
.captcha-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.captcha-img {
  width: 120px;
  height: 40px;
  border-radius: 6px;
  border: 1px solid var(--td-component-border);
  cursor: pointer;
  flex-shrink: 0;
}

.captcha-loading {
  width: 120px;
  height: 40px;
  border-radius: 6px;
  border: 1px solid var(--td-component-border);
  cursor: pointer;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--td-bg-color-secondarycontainer);
  color: var(--td-text-color-placeholder);
}

.captcha-loading:hover {
  background: var(--td-bg-color-container-hover);
}

.form-footer {
  text-align: center;
  margin-top: 8px;
}

/* Responsive */
@media (max-width: 768px) {
  .login-brand {
    display: none;
  }
  .login-form-panel {
    padding: 24px;
  }
}
</style>
