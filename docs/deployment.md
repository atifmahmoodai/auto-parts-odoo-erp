# Deployment, release and recovery

## First installation

Use a dedicated host and approved domain. Restrict inbound traffic to HTTPS/HTTP and administration from approved sources. PostgreSQL and Odoo application ports have no host port mappings. The database network is internal. Caddy obtains certificates for the configured hostname; configure DNS first. Keep the proxy stopped until the administrator has been changed and company settings reviewed.

1. Copy `.env.example` to `.env`; `chmod 600 .env`. Generate three independent random secrets (for example `openssl rand -hex 32`): PostgreSQL administrator, Odoo database role, Odoo database-manager master password. Never commit them. The runtime rejects database/master passwords shorter than 32 characters or equal to one another.
2. Export `INITIAL_ADMIN_LOGIN` and a unique `INITIAL_ADMIN_PASSWORD` of at least 20 characters through your secret manager or a private shell. Run `bash scripts/initialize.sh`. It initializes the native module, replaces the default administrator login/password, then disables scheduled actions. If initialization fails, **do not start the proxy**; inspect logs and complete administrator setup privately. The script refuses an installed database and will not erase or reinstall it.
3. Unset those initial administrator variables. Save credentials in the approved secret manager. Use a temporary localhost-only SSH-forwarded application access or approved private network to finish configuration. Do not publish a default-admin instance.
4. Set company name/address/currency/timezone, approved localization and chart, tax mappings, journal sequences and lock dates with the client's accountant. No production localization is chosen in this repository.
5. Create named staff accounts with minimum required native roles. Verify each account sees only approved companies. Inventory administrators can import; warehouse operators can receive and transfer but cannot apply this importer. Review the administrator's broad native powers. Enable Odoo's supported authentication hardening according to client policy.
6. SMTP is pointed at an unavailable localhost port and scheduled actions are disabled at bootstrap. Configure approved email transport, sender domain and recipients, then individually enable reviewed scheduled actions. Do not mass-enable cron with unreviewed imported records.
7. Complete the acceptance checklist. Start `docker compose up -d`. Check HTTPS, `/web/login`, company restrictions and background jobs. Application configuration is rendered with mode 0600 inside the container.

Database role `odoo` is NOSUPERUSER/NOCREATEDB/NOCREATEROLE; the single `parts` database is created by PostgreSQL bootstrap and assigned to it. Database listing is disabled and `dbfilter` allows only `parts`. The Odoo master password is separate from the administrator user password. Never expose PostgreSQL or the database manager as a backup service.

## Upgrade

Record the repository commit and `docker image inspect` RepoDigests for Odoo, PostgreSQL and Caddy. Take a consistent backup, restore it in isolated staging and test the release there. Stop proxy/application writers in a maintenance window, then:

```sh
docker compose run --rm odoo odoo -d parts -u auto_parts_dealer --stop-after-init --max-cron-threads=0
docker compose up -d
```

Check logs and repeat the receiving/transfer/sales/invoicing acceptance flow with approved test data in staging. A major Odoo or PostgreSQL upgrade requires a separate migration plan; do not change major image versions directly on live volumes. Reverting code does not undo schema/data migrations: rollback requires the matching database and filestore snapshot.

## Backup and restoration

`bash scripts/backup.sh` stops proxy/Odoo writers, dumps PostgreSQL in custom format, archives the matching Odoo filestore and records checksums, then restarts services via an EXIT trap. It assumes the stack is normally running. Plan downtime and verify no other integrations write directly to the database. Copy the backup off-host using approved encryption and access controls. `.env` credentials are intentionally excluded; recover them separately from the secret manager.

Restore only into an isolated, disposable staging stack with separate volumes, no public proxy and no live email integrations:

1. Verify `sha256sum -c backups/TIMESTAMP/SHA256SUMS` from the same repository path, and record the matching code/images.
2. Stop all application writers. Create a clean target database owned by `odoo`. Use `pg_restore -U odoo --no-owner --exit-on-error -d parts` through the database container. **Do not restore over a populated production database.**
3. Extract the matching archive into the staging Odoo data volume so the path remains `/var/lib/odoo/filestore/parts/`; preserve file permissions/owner for the Odoo image user.
4. Disable scheduled actions and remove outgoing transport credentials on the restored staging database before starting the app. Confirm administrators, documents/attachments, company access, product counts, stock by location and financial balances against the signed backup record.
5. Record restore duration, recovery point, checksums, reviewer and discrepancies. Retest quarterly and before every release.

CI exercises database dump/restore and addon upgrade, not a client's full off-host disaster recovery or filestore recovery. Establish agreed RPO/RTO, retention, monitoring and an off-host restoration drill before client go-live.
