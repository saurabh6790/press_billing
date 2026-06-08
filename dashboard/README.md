# Billing Dashboard (Frappe-UI SPA)

The customer billing portal (#18) and admin dashboard (#19), built on the same
stack `frappe/press` ships its dashboard on: **Vue 3 + Vite + Vue Router + Pinia
+ frappe-ui**, with the `frappe-ui/tailwind` preset as the *sole* source of
colour tokens (press parity — no bespoke palette).

## Build

    cd apps/billing/dashboard
    yarn install
    yarn build        # -> ../billing/public/dashboard/ (served at /assets/billing/dashboard/)

Then open **/billing** on the site (served by `www/billing.html`; deep links
under `/billing/*` resolve via the website route rule). For live development:
`yarn dev` (proxies /api,/assets to http://localhost:8000).

Built output and node_modules are gitignored — run the build to (re)generate them.
