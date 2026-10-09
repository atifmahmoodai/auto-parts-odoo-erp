#!/bin/bash
# Maintenance-window backup: stop all application writers, copy DB and matching filestore.
set -euo pipefail
umask 077
mkdir -p backups
stamp=$(date -u +%Y%m%dT%H%M%SZ)
target="backups/$stamp"
mkdir "$target"
docker compose stop proxy odoo
trap 'docker compose start odoo proxy' EXIT
docker compose exec -T db pg_dump -U odoo -Fc parts > "$target/database.dump"
docker compose run --rm --no-deps --entrypoint tar odoo -C /var/lib/odoo -czf - filestore > "$target/filestore.tar.gz"
cp compose.yaml "$target/compose.yaml"
sha256sum "$target/database.dump" "$target/filestore.tar.gz" > "$target/SHA256SUMS"
echo "Created $target. Encrypt and copy off-host; a backup is not verified until restored in an isolated environment."
