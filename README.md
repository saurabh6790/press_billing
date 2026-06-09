### Billing

Billing & payments system of record for Frappe Cloud v2

### Documentation

New here? Start with **[docs/](docs/README.md)** — a guided set covering the
overview, onboarding, architecture, configuration, end-to-end workflows (with
diagrams), the action/API reference, and a glossary.

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch fc-prod
bench install-app billing
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/billing
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit
