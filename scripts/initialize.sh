#!/bin/bash
# Run from repository root, before starting the proxy. Fresh databases ONLY.
set -euo pipefail
: "${INITIAL_ADMIN_LOGIN:?Export the approved administrator email}"
: "${INITIAL_ADMIN_PASSWORD:?Export a unique administrator password}"
if [ "${#INITIAL_ADMIN_PASSWORD}" -lt 20 ]; then echo 'Use at least 20 characters for the administrator password.' >&2; exit 1; fi
docker compose up -d db
# Do not accidentally reinstall/reconfigure a populated system.
if docker compose exec -T db psql -U postgres -d parts -Atc "SELECT to_regclass('public.ir_module_module')" | grep -q ir_module_module; then
  echo 'Database already initialized. Use the documented upgrade process.' >&2; exit 1
fi
docker compose run --rm odoo odoo -d parts -i auto_parts_dealer --without-demo=all --stop-after-init --max-cron-threads=0
docker compose run --rm -T -e INITIAL_ADMIN_LOGIN -e INITIAL_ADMIN_PASSWORD odoo odoo shell -d parts --no-http <<'PY'
import os
admin = env.ref('base.user_admin')
admin.write({'login': os.environ['INITIAL_ADMIN_LOGIN'], 'password': os.environ['INITIAL_ADMIN_PASSWORD']})
env['ir.cron'].search([]).write({'active': False})
env.cr.commit()
PY
echo 'Initialized with a private administrator login; scheduled actions are disabled. Complete acceptance before starting the proxy.'
