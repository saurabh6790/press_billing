import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import frappeui from 'frappe-ui/vite';
import path from 'path';

export default defineConfig(({ command }) => ({
  plugins: [frappeui({ frappeProxy: true, lucideIcons: true, jinjaBootData: false, buildConfig: false }), vue()],
  base: command === 'build' ? '/assets/billing/dashboard/' : '/',
  resolve: { alias: { '@': path.resolve(__dirname, 'src') } },
  optimizeDeps: {
    include: ['feather-icons', 'debug'],
    esbuildOptions: {
      plugins: [{
        name: 'lucide-icons-stub',
        setup(build) {
          build.onResolve({ filter: /^~icons\/lucide\// }, (args) => ({ path: args.path, namespace: 'lucide-stub' }));
          build.onLoad({ filter: /.*/, namespace: 'lucide-stub' }, () => ({ contents: 'export default {}', loader: 'js' }));
        },
      }],
    },
  },
  build: {
    outDir: path.resolve(__dirname, '../billing/public/dashboard'),
    emptyOutDir: true,
    sourcemap: false,
  },
}));
