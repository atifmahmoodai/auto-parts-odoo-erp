#!/bin/bash
set -euo pipefail
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set=odoo_password="$ODOO_DB_PASSWORD" --set=ON_ERROR_STOP=1 <<'SQL'
CREATE ROLE odoo LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'odoo_password';
ALTER DATABASE parts OWNER TO odoo;
REVOKE ALL ON DATABASE parts FROM PUBLIC;
GRANT ALL ON SCHEMA public TO odoo;
SQL
