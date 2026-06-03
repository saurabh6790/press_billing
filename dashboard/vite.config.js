import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import frappeui from 'frappe-ui/vite';
import path from 'path';

// frappeui() wires the lucide-icons resolver, the Frappe dev proxy and the
// build config (the same setup press uses). Built assets land in the app's
// public/ and are served at /assets/press_billing/dashboard/.
export default defineConfig({
  plugins: [frappeui({ frappeProxy: true, lucideIcons: true, jinjaBootData: false, buildConfig: false }), vue()],
  base: '/assets/press_billing/dashboard/',
  resolve: { alias: { '@': path.resolve(__dirname, 'src') } },
  build: {
    outDir: path.resolve(__dirname, '../press_billing/public/dashboard'),
    emptyOutDir: true,
    sourcemap: false,
    rollupOptions: {
      output: {
        // Stable entry names so the Frappe www page can reference them.
        entryFileNames: 'assets/index.js',
        chunkFileNames: 'assets/[name].js',
        assetFileNames: 'assets/[name][extname]',
      },
    },
  },
});
