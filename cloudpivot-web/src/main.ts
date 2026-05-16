import { createApp } from 'vue';
import TDesign from 'tdesign-vue-next';
import 'tdesign-vue-next/es/style/index.css';
import App from './App.vue';
import router from './router';
import { createPinia } from 'pinia';
import i18n from './locales';

const app = createApp(App);
app.use(TDesign);
app.use(createPinia());
app.use(router);
app.use(i18n);
app.mount('#app');
