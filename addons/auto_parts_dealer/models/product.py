import re
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    ap_is_part = fields.Boolean('Auto part', default=False, index=True, tracking=True)
    ap_source_key = fields.Char('Catalog source key', copy=False, index=True, tracking=True,
                               help='Stable source-system identifier for this product template, not a vehicle fitment claim.')
    ap_brand = fields.Char('Part manufacturer / brand', index=True, tracking=True)
    ap_oem_reference = fields.Char('OEM reference', index=True, tracking=True,
                                  help='Supplier-provided reference only. Verify suitability separately.')
    ap_condition = fields.Selection([('new', 'New'), ('remanufactured', 'Remanufactured'),
                                     ('used', 'Used')], default='new', string='Part condition', tracking=True)
    _ap_source_company_unique = models.Constraint(
        'UNIQUE(company_id, ap_source_key)', 'Catalog source keys must be unique within a company.')

    @api.constrains('ap_is_part', 'ap_source_key', 'company_id', 'type', 'is_storable', 'ap_condition')
    def _check_auto_part(self):
        for product in self.filtered('ap_is_part'):
            if not product.company_id:
                raise ValidationError(_('Auto parts need an explicit company.'))
            if not product.ap_source_key or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,64}', product.ap_source_key):
                raise ValidationError(_('Use a stable catalog key containing letters, digits, dot, underscore, colon or dash.'))
            if product.type != 'consu' or not product.is_storable or not product.ap_condition:
                raise ValidationError(_('Auto parts must be inventory-tracked goods with a condition.'))

    def write(self, vals):
        for product in self.filtered('ap_source_key'):
            if ('ap_source_key' in vals and vals['ap_source_key'] != product.ap_source_key) or (
                    'company_id' in vals and vals['company_id'] != product.company_id.id):
                raise ValidationError(_('The source key and company are immutable once a part is created. Archive and create a corrected record instead.'))
        return super().write(vals)
