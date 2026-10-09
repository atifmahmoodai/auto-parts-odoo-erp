"""Strict, dependency-free catalog input contract shared by the Odoo model and local tests."""
import csv
import hashlib
import io
import re
from decimal import Decimal, InvalidOperation

COLUMNS = ['source_key', 'name', 'sku', 'barcode', 'brand', 'oem_reference', 'condition',
           'sale_price', 'cost', 'uom_external_id', 'category_external_id']


def parse_catalog(raw):
    if not raw or len(raw) > 2 * 1024 * 1024:
        raise ValueError('Upload a nonempty UTF-8 CSV under 2 MB.')
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError as error:
        raise ValueError('CSV must use UTF-8 encoding.') from error
    if '\x00' in text:
        raise ValueError('NUL bytes are not allowed.')
    reader = csv.DictReader(io.StringIO(text), strict=True)
    if reader.fieldnames != COLUMNS:
        raise ValueError('CSV columns must exactly match the supplied template, in order.')
    rows, keys, skus, barcodes = [], set(), set(), set()
    try:
        for number, item in enumerate(reader, 2):
            if len(rows) >= 1000:
                raise ValueError('Use batches of at most 1,000 rows.')
            if None in item or any(value is None for value in item.values()):
                raise ValueError(f'Row {number}: unexpected or missing columns.')
            row = {key: value.strip() for key, value in item.items()}
            if any(len(value) > 200 or any(ord(c) < 32 for c in value) for value in row.values()):
                raise ValueError(f'Row {number}: fields must be single-line text of at most 200 characters.')
            if not re.fullmatch(r'[A-Za-z0-9_.:-]{1,64}', row['source_key']) or not row['name'] or not row['sku']:
                raise ValueError(f'Row {number}: source key, name and SKU are required.')
            for field, seen in [('source_key', keys), ('sku', skus), ('barcode', barcodes)]:
                if row[field] and row[field] in seen:
                    raise ValueError(f'Row {number}: duplicate {field}.')
                seen.add(row[field])
            if row['condition'] not in ('new', 'remanufactured', 'used'):
                raise ValueError(f'Row {number}: invalid condition.')
            for field in ['sale_price', 'cost']:
                try:
                    if not re.fullmatch(r'[0-9]+(?:\.[0-9]{1,4})?', row[field]):
                        raise InvalidOperation
                    amount = Decimal(row[field])
                    if not amount.is_finite() or amount < 0 or amount > Decimal('1000000000') or amount.as_tuple().exponent < -4:
                        raise InvalidOperation
                    row[field] = format(amount, 'f')
                except InvalidOperation as error:
                    raise ValueError(f'Row {number}: {field} must be nonnegative, bounded and have at most four decimals.') from error
            for field in ['uom_external_id', 'category_external_id']:
                if not re.fullmatch(r'[A-Za-z0-9_]+\.[A-Za-z0-9_]+', row[field]):
                    raise ValueError(f'Row {number}: use a valid external ID for {field}.')
            rows.append(row)
    except csv.Error as error:
        raise ValueError('Malformed CSV quoting.') from error
    if not rows:
        raise ValueError('The CSV contains no product rows.')
    return rows, hashlib.sha256(raw).hexdigest()
