import base64
import binascii
import hashlib
import json
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError
from odoo.tools.float_utils import float_compare
from .catalog_csv import parse_catalog


class CatalogImport(models.Model):
    _name = 'ap.catalog.import'
    _description = 'Reviewed Parts Catalog Import'
    _order = 'create_date desc, id desc'
    _check_company_auto = True

    name = fields.Char(required=True, default='Parts catalog migration')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    file = fields.Binary('CSV file', required=True, attachment=False)
    filename = fields.Char()
    state = fields.Selection([('draft', 'Draft'), ('validated', 'Ready for review'), ('applied', 'Applied')], default='draft', readonly=True)
    digest = fields.Char('File SHA-256', readonly=True)
    plan_fingerprint = fields.Char(readonly=True)
    preview = fields.Text('Review summary', readonly=True)
    row_count = fields.Integer(readonly=True)
    applied_at = fields.Datetime(readonly=True)
    applied_by = fields.Many2one('res.users', readonly=True)
    product_ids = fields.Many2many('product.template', readonly=True)

    _editable = {'name', 'company_id', 'file', 'filename'}

    @api.model
    def _validate_input_size(self, vals):
        if vals.get('file') and len(vals['file']) > 2800000:
            raise UserError(_('The encoded upload is too large; use a CSV under 2 MB.'))
        if any(len(vals.get(key) or '') > 200 for key in ['name', 'filename']):
            raise UserError(_('Names must be at most 200 characters.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._validate_input_size(vals)
            if set(vals) - self._editable:
                raise AccessError(_('Import result fields cannot be supplied by callers.'))
        # Context defaults are caller-controlled too; never inherit result metadata.
        safe_vals = [dict(vals, state='draft', digest=False, plan_fingerprint=False, preview=False,
                          row_count=0, applied_at=False, applied_by=False, product_ids=[fields.Command.clear()])
                     for vals in vals_list]
        return super().create(safe_vals)

    def write(self, vals):
        self._validate_input_size(vals)
        if set(vals) - self._editable:
            raise AccessError(_('Use Validate and Apply; result fields are server-managed.'))
        if any(batch.state == 'applied' for batch in self):
            raise UserError(_('Applied imports are immutable. Create a new batch.'))
        vals = dict(vals, state='draft', digest=False, plan_fingerprint=False, preview=False, row_count=0)
        return super().write(vals)

    def unlink(self):
        if any(batch.state == 'applied' for batch in self):
            raise UserError(_('Retain applied imports as migration evidence.'))
        return super().unlink()

    def _authorize(self):
        self.ensure_one()
        self.check_access('write')
        if (not self.env.user.has_group('stock.group_stock_manager')
                or not self.env.user.has_group('product.group_product_manager')
                or self.company_id not in self.env.companies):
            raise AccessError(_('Inventory administrator and product management permissions with this company selected are required.'))

    def _plan(self):
        self._authorize()
        try:
            raw = base64.b64decode(self.with_context(bin_size=False).file or b'', validate=True)
            rows, digest = parse_catalog(raw)
        except (ValueError, binascii.Error) as error:
            raise UserError(str(error)) from error
        products = self.env['product.template'].with_company(self.company_id).with_context(active_test=False)
        plan, snapshot = [], []
        for number, row in enumerate(rows, 2):
            old = products.search([('company_id', '=', self.company_id.id), ('ap_source_key', '=', row['source_key'])])
            if old and (not old.active or not old.ap_is_part or old.product_variant_count != 1):
                raise UserError(_('Row %s: archived, non-part or multi-variant records require manual review.', number))
            uom = self.env.ref(row['uom_external_id'], raise_if_not_found=False)
            category = self.env.ref(row['category_external_id'], raise_if_not_found=False)
            if not uom or uom._name != 'uom.uom' or not category or category._name != 'product.category':
                raise UserError(_('Row %s: unit/category external ID is missing or has the wrong model.', number))
            uom.check_access('read'); category.check_access('read')
            for field in ['default_code', 'barcode']:
                value = row['sku'] if field == 'default_code' else row['barcode']
                if value and self.env['product.product'].with_context(active_test=False).search_count([
                        (field, '=', value), ('company_id', 'in', [False, self.company_id.id]),
                        ('product_tmpl_id', 'not in', old.ids)]):
                    raise UserError(_('Row %s: SKU/barcode already belongs to a different product.', number))
            if old and (old.uom_id != uom or old.categ_id != category):
                raise UserError(_('Row %s: change existing units/categories through a reviewed native Odoo workflow.', number))
            if old and float_compare(old.standard_price, float(row['cost']), precision_digits=4):
                raise UserError(_('Row %s: this importer cannot change existing inventory cost. Use Odoo valuation controls.', number))
            vals = {'name': row['name'], 'default_code': row['sku'], 'barcode': row['barcode'] or False,
                    'ap_brand': row['brand'], 'ap_oem_reference': row['oem_reference'], 'ap_condition': row['condition'],
                    'list_price': float(row['sale_price'])}
            if not old:
                vals.update(company_id=self.company_id.id, ap_is_part=True, ap_source_key=row['source_key'],
                            type='consu', is_storable=True, uom_id=uom.id, categ_id=category.id,
                            standard_price=float(row['cost']), sale_ok=True, purchase_ok=True)
            plan.append((old, vals))
            snapshot.append({'source': row['source_key'], 'id': old.id or None,
                             'write_date': str(old.write_date) if old else None,
                             'values': old.read(['name', 'default_code', 'barcode', 'ap_brand', 'ap_oem_reference',
                                                 'ap_condition', 'list_price', 'standard_price', 'uom_id', 'categ_id',
                                                 'active', 'ap_is_part', 'product_variant_count'])[0] if old else None,
                             'variant_write_date': str(old.product_variant_id.write_date) if old else None,
                             'uom_write_date': str(uom.write_date), 'category_write_date': str(category.write_date)})
        fingerprint = hashlib.sha256(json.dumps({'file': digest, 'company': self.company_id.id, 'snapshot': snapshot}, sort_keys=True).encode()).hexdigest()
        return plan, digest, fingerprint

    def action_validate(self):
        self._authorize()
        if self.state == 'applied':
            raise UserError(_('This batch is already applied.'))
        plan, digest, fingerprint = self._plan()
        created = sum(not old for old, _ in plan)
        summary = _('%s rows: %s new products and %s existing products. Prices/costs use the selected company currency. No quantities, taxes, invoices, vendor bills or journal entries are imported.\n\n', len(plan), created, len(plan)-created)
        lines = []
        for old, vals in plan:
            lines.append(('UPDATE ' if old else 'CREATE ') + vals['default_code'] + ' — ' + vals['name'])
            lines.append('  Brand: %s | OEM: %s | Condition: %s | Sale price: %s | Cost: %s' % (
                vals['ap_brand'] or '—', vals['ap_oem_reference'] or '—', vals['ap_condition'],
                vals['list_price'], old.standard_price if old else vals['standard_price']))
            if old:
                changes = {key: {'before': old[key], 'after': value} for key, value in vals.items() if old[key] != value}
                lines.append('  Changes: ' + json.dumps(changes, ensure_ascii=False, sort_keys=True))
        summary += '\n'.join(lines)
        super().write({'state': 'validated', 'digest': digest, 'plan_fingerprint': fingerprint, 'preview': summary, 'row_count': len(plan)})
        return True

    def action_apply(self):
        self._authorize()
        # Serialize imports in this company, including different batch records with overlapping keys.
        self.env.cr.execute('SELECT pg_advisory_xact_lock(%s, %s)', [192601, self.company_id.id])
        self.env.cr.execute('SELECT id FROM ap_catalog_import WHERE id = %s FOR UPDATE', [self.id])
        self.env.cr.execute('SELECT id FROM product_template WHERE company_id = %s AND ap_is_part ORDER BY id FOR UPDATE', [self.company_id.id])
        self.env.cr.execute('SELECT p.id FROM product_product p JOIN product_template t ON t.id=p.product_tmpl_id WHERE t.company_id=%s AND t.ap_is_part ORDER BY p.id FOR UPDATE OF p', [self.company_id.id])
        self.env['product.template'].invalidate_model()
        self.env['product.product'].invalidate_model()
        self.invalidate_recordset()
        if self.state == 'applied':
            return True
        if self.state != 'validated':
            raise UserError(_('Validate and review the batch before applying.'))
        # Recheck after locking; no sudo and no privilege escalation.
        plan, digest, fingerprint = self._plan()
        if digest != self.digest or fingerprint != self.plan_fingerprint:
            raise UserError(_('The file or catalog changed since validation. Validate again and review the new plan.'))
        result = self.env['product.template']
        with self.env.cr.savepoint():
            for old, vals in plan:
                if old:
                    old.write(vals); result |= old
                else:
                    result |= self.env['product.template'].with_company(self.company_id).create(vals)
            super().write({'state': 'applied', 'applied_at': fields.Datetime.now(), 'applied_by': self.env.user.id,
                           'product_ids': [fields.Command.set(result.ids)]})
        return True
