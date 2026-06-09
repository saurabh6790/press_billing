import { createRouter, createWebHistory } from 'vue-router';
const routes = [
  { path: '/', redirect: '/billing' },
  { path: '/billing', name: 'Overview', component: () => import('@/pages/Overview.vue') },
  { path: '/billing/forecast', name: 'Forecast', component: () => import('@/pages/Forecast.vue') },
  { path: '/billing/invoices', name: 'Invoices', component: () => import('@/pages/Invoices.vue') },
  { path: '/billing/payments', name: 'PaymentHistory', component: () => import('@/pages/PaymentHistory.vue') },
  { path: '/billing/credits', name: 'Credits', component: () => import('@/pages/Credits.vue') },
  { path: '/billing/methods', name: 'PaymentMethods', component: () => import('@/pages/PaymentMethods.vue') },
  { path: '/billing/tier', name: 'TrustTier', component: () => import('@/pages/TrustTier.vue') },
  { path: '/billing/admin', name: 'AdminOverview', component: () => import('@/pages/AdminOverview.vue') },
  { path: '/billing/admin/teams', name: 'AdminTeams', component: () => import('@/pages/AdminTeams.vue') },
  { path: '/billing/admin/invoices', name: 'AdminInvoices', component: () => import('@/pages/AdminInvoices.vue') },
  { path: '/billing/admin/catalog', name: 'AdminCatalog', component: () => import('@/pages/AdminCatalog.vue') },
  { path: '/billing/admin/clusters', name: 'AdminClusters', component: () => import('@/pages/AdminClusters.vue') },
  { path: '/billing/admin/plans', name: 'AdminPlans', component: () => import('@/pages/AdminPlans.vue') },
  { path: '/billing/admin/failures', name: 'AdminFailures', component: () => import('@/pages/AdminFailures.vue') },
  { path: '/billing/admin/trials', name: 'AdminTrials', component: () => import('@/pages/AdminTrials.vue') },
  { path: '/billing/admin/retention', name: 'AdminRetention', component: () => import('@/pages/AdminRetention.vue') },
];
export default createRouter({ history: createWebHistory('/'), routes });
