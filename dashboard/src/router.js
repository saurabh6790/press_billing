import { createRouter, createWebHistory } from 'vue-router';

const routes = [
  { path: '/', redirect: '/billing' },
  { path: '/billing', name: 'Overview', component: () => import('@/pages/Overview.vue') },
  { path: '/billing/invoices', name: 'Invoices', component: () => import('@/pages/Invoices.vue') },
  { path: '/billing/methods', name: 'PaymentMethods', component: () => import('@/pages/PaymentMethods.vue') },
  { path: '/billing/credits', name: 'Credits', component: () => import('@/pages/Credits.vue') },
  { path: '/billing/admin', name: 'Admin', component: () => import('@/pages/Admin.vue') },
];

export default createRouter({
  history: createWebHistory('/billing'),
  routes,
});
