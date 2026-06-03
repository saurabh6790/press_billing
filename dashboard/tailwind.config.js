import frappeUIPreset from 'frappe-ui/tailwind';

// Press parity: the frappe-ui preset is the SOLE source of colour tokens,
// spacing and typography. No bespoke palette is defined here.
export default {
  presets: [frappeUIPreset],
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}',
    './node_modules/frappe-ui/src/components/**/*.{vue,js,ts}',
  ],
  theme: { extend: {} },
  plugins: [],
};
