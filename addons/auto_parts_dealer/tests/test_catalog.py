import base64
from odoo import fields
from odoo.tests import TransactionCase, tagged, new_test_user
from odoo.exceptions import AccessError, UserError, ValidationError

HEADER = 'source_key,name,sku,barcode,brand,oem_reference,condition,sale_price,cost,uom_external_id,category_external_id\n'
ROW = 'TEST-001,Test oil filter,TEST-OF-001,TESTBAR001,Example Parts,EX-OEM-100,new,24.50,12.00,uom.product_uom_unit,auto_parts_dealer.category_parts\n'


@tagged('post_install', '-at_install')
class TestCatalogMigration(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = new_test_user(cls.env, login='parts_manager', groups='stock.group_stock_manager,product.group_product_manager', context={'no_reset_password': True},
                                    company_id=cls.env.company.id, company_ids=[fields.Command.set(cls.env.company.ids)])
        cls.stock_user = new_test_user(cls.env, login='parts_operator', groups='stock.group_stock_user', context={'no_reset_password': True},
                                      company_id=cls.env.company.id, company_ids=[fields.Command.set(cls.env.company.ids)])

    def batch(self, text=None):
        return self.env['ap.catalog.import'].with_user(self.manager).create({
            'name': 'Fictional test import', 'file': base64.b64encode((text or HEADER+ROW).encode()),
            'company_id': self.env.company.id, 'filename': 'test.csv'})

    def test_review_and_idempotent_apply(self):
        batch = self.batch()
        with self.assertRaises(UserError):batch.action_apply()
        batch.action_validate()
        self.assertEqual(batch.state, 'validated')
        self.assertFalse(batch.product_ids)
        batch.action_apply();batch.action_apply()
        self.assertEqual(len(batch.product_ids), 1)
        self.assertEqual(batch.product_ids.ap_source_key, 'TEST-001')
        self.assertEqual(batch.product_ids.standard_price, 12)
        self.assertEqual(batch.product_ids.qty_available, 0)
        self.assertEqual(batch.applied_by, self.manager)

    def test_applied_record_cannot_be_forged_edited_or_deleted(self):
        with self.assertRaises(AccessError):self.env['ap.catalog.import'].create({'name':'Forged','file':b'AA==','state':'applied'})
        batch = self.batch();batch.action_validate();batch.action_apply()
        with self.assertRaises(UserError):batch.write({'name':'Changed'})
        with self.assertRaises(UserError):batch.unlink()
        with self.assertRaises(AccessError):batch.write({'state':'draft'})

    def test_context_cannot_forge_import_results(self):
        batch = self.env['ap.catalog.import'].with_user(self.manager).with_context(
            default_state='applied', default_digest='forged', default_applied_by=self.manager.id,
            default_row_count=999).create({'file':base64.b64encode((HEADER+ROW).encode())})
        self.assertEqual(batch.state, 'draft')
        self.assertFalse(batch.digest)
        self.assertFalse(batch.applied_by)
        self.assertEqual(batch.row_count, 0)
        with self.assertRaises(UserError): batch.action_apply()

    def test_existing_updates_and_stale_review(self):
        first = self.batch();first.action_validate();first.action_apply()
        second = self.batch((HEADER+ROW).replace('Test oil filter','Updated oil filter'))
        second.action_validate()
        first.product_ids.write({'name':'Manual intervening edit'})
        with self.assertRaises(UserError):second.action_apply()
        second.action_validate();second.action_apply()
        self.assertEqual(second.product_ids, first.product_ids)
        self.assertEqual(second.product_ids.name, 'Updated oil filter')

    def test_cost_change_and_duplicate_sku_rejected(self):
        batch = self.batch();batch.action_validate();batch.action_apply()
        with self.assertRaises(UserError):self.batch((HEADER+ROW).replace('12.00','13.00')).action_validate()
        with self.assertRaises(UserError):self.batch((HEADER+ROW).replace('TEST-001','TEST-002')).action_validate()

    def test_file_edit_resets_validation(self):
        batch = self.batch();batch.action_validate();batch.write({'file':base64.b64encode((HEADER+ROW).replace('24.50','25.00').encode())})
        self.assertEqual(batch.state,'draft')
        with self.assertRaises(UserError):batch.action_apply()

    def test_operator_and_company_boundaries(self):
        batch = self.batch()
        with self.assertRaises(AccessError):batch.with_user(self.stock_user).action_validate()
        company = self.env['res.company'].create({'name':'Other fictional company'})
        other = self.env['ap.catalog.import'].create({'company_id':company.id,'file':base64.b64encode((HEADER+ROW).encode())})
        with self.assertRaises(AccessError):other.with_user(self.manager).action_validate()
        self.assertFalse(self.env['ap.catalog.import'].with_user(self.manager).search([('id','=',other.id)]))

    def test_part_identity_and_inventory_constraints(self):
        batch=self.batch();batch.action_validate();batch.action_apply();part=batch.product_ids
        for vals in [{'ap_source_key':'different'},{'company_id':False},{'is_storable':False}]:
            with self.assertRaises(ValidationError), self.cr.savepoint():part.write(vals)

    def test_bad_later_row_creates_nothing(self):
        text=HEADER+ROW+ROW.replace('TEST-001','TEST-002').replace('TEST-OF-001','TEST-OF-002').replace('TESTBAR001','TESTBAR002').replace('uom.product_uom_unit','missing.unit')
        batch=self.batch(text)
        with self.assertRaises(UserError):batch.action_validate()
        self.assertFalse(self.env['product.template'].search([('ap_source_key','in',['TEST-001','TEST-002'])]))
