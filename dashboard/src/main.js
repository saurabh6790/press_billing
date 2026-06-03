import { createApp } from 'vue';
import { createPinia } from 'pinia';
import { FrappeUI, setConfig, frappeRequest } from 'frappe-ui';
import App from './App.vue';
import router from './router';
import './index.css';

// All client data goes through frappe-ui resources -> whitelisted endpoints.
setConfig('resourceFetcher', frappeRequest);

const app = createApp(App);
app.use(createPinia());
app.use(router);
app.use(FrappeUI);
app.mount('#app');
