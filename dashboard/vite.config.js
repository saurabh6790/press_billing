import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import frappeui from 'frappe-ui/vite';
import path from 'path';

export default defineConfig({
  plugins: [frappeui({ frappeProxy: true, lucideIcons: true, jinjaBootData: false, buildConfig: false }), vue()],
  base: '/assets/billing/dashboard/',
  resolve: { alias: { '@': path.resolve(__dirname, 'src') } },
  build: {
    outDir: path.resolve(__dirname, '../billing/public/dashboard'),
    emptyOutDir: true,
    sourcemap: false,
    // Content-hashed filenames -> browsers always fetch the right version.
  },
});
