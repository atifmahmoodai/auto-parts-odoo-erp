#!/usr/bin/env python3
"""Render private Odoo configuration without committing credentials."""
import configparser
import os
from pathlib import Path

config = configparser.ConfigParser(interpolation=None)
password = os.environ.get('ODOO_DB_PASSWORD', '')
master = os.environ.get('ODOO_MASTER_PASSWORD', '')
if min(len(password), len(master)) < 32 or password == master:
    raise SystemExit('Set distinct database and master passwords of at least 32 characters.')
config['options'] = {
    'addons_path': '/mnt/extra-addons', 'data_dir': '/var/lib/odoo',
    'db_host': 'db', 'db_port': '5432', 'db_user': 'odoo', 'db_password': password,
    'db_name': 'parts', 'dbfilter': '^parts$', 'list_db': 'False',
    'admin_passwd': master, 'proxy_mode': 'True', 'workers': '2',
    'max_cron_threads': '1', 'limit_time_cpu': '120', 'limit_time_real': '240',
    'limit_memory_soft': '2147483648', 'limit_memory_hard': '2684354560',
    'log_level': 'info', 'smtp_server': '127.0.0.1', 'smtp_port': '1',
}
path = Path('/tmp/parts-odoo.conf')
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, 'w') as stream:
    config.write(stream)
import sys
command = sys.argv[1:] or ['odoo']
os.execvp(command[0], command + ['--config', str(path)])
