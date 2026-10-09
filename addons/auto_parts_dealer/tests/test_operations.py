from odoo import Command, fields
from odoo.tests import tagged
from odoo.exceptions import AccessError
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestNativePartsOperations(AccountTestInvoicingCommon):
    country_code = 'US'
    chart_template = 'us'

    @classmethod
    def get_default_groups(cls):
        return super().get_default_groups() | cls.env.ref('sales_team.group_sale_manager')

    def test_purchase_receive_transfer_sell_invoice_and_bill(self):
        # US accounting is a disposable TEST fixture, never installed as the client's localization.
        company=self.env.company
        warehouse=self.env['stock.warehouse'].search([('company_id','=',company.id)],limit=1)
        if not warehouse:
            warehouse=self.env['stock.warehouse'].create({'name':'Fictional Main','code':'TMAIN','company_id':company.id})
        second=self.env['stock.warehouse'].create({'name':'Fictional Second','code':'TSEC','company_id':company.id})
        vendor=self.env['res.partner'].create({'name':'Fictional Parts Vendor','supplier_rank':1})
        customer=self.env['res.partner'].create({'name':'Fictional Workshop Customer','customer_rank':1})
        template=self.env['product.template'].create({'name':'Fictional tested filter','company_id':company.id,
            'ap_is_part':True,'ap_source_key':'FLOW-001','default_code':'FLOW-001','ap_brand':'Example Parts',
            'type':'consu','is_storable':True,'standard_price':12,'list_price':25,'invoice_policy':'delivery',
            'purchase_method':'receive','categ_id':self.product_category.id,
            'taxes_id':[Command.clear()],'supplier_taxes_id':[Command.clear()]})
        product=template.product_variant_id
        purchase=self.env['purchase.order'].create({'partner_id':vendor.id,'picking_type_id':warehouse.in_type_id.id,
            'order_line':[Command.create({'product_id':product.id,'name':product.name,'product_qty':10,
                'product_uom_id':product.uom_id.id,'price_unit':12,'date_planned':fields.Datetime.now(),'tax_ids':[Command.clear()]})]})
        purchase.button_confirm();receipt=purchase.picking_ids
        receipt.move_ids.write({'quantity':10,'picked':True});receipt.button_validate()
        self.assertEqual(receipt.state,'done')
        self.assertEqual(product.with_context(warehouse_id=warehouse.id).qty_available,10)
        transfer=self.env['stock.picking'].create({'picking_type_id':warehouse.int_type_id.id,
            'location_id':warehouse.lot_stock_id.id,'location_dest_id':second.lot_stock_id.id,
            'move_ids':[Command.create({'name':'Fictional transfer','product_id':product.id,'product_uom_qty':4,
                'product_uom':product.uom_id.id,'location_id':warehouse.lot_stock_id.id,'location_dest_id':second.lot_stock_id.id})]})
        transfer.action_confirm();transfer.action_assign();transfer.move_ids.write({'quantity':4,'picked':True});transfer.button_validate()
        self.assertEqual(transfer.state,'done')
        sale=self.env['sale.order'].create({'partner_id':customer.id,'warehouse_id':second.id,
            'order_line':[Command.create({'product_id':product.id,'product_uom_qty':2,'price_unit':25,'tax_ids':[Command.clear()]})]})
        sale.action_confirm();delivery=sale.picking_ids
        delivery.action_assign();delivery.move_ids.write({'quantity':2,'picked':True});delivery.button_validate()
        self.assertEqual(delivery.state,'done')
        self.assertEqual(product.with_context(warehouse_id=warehouse.id).qty_available,6)
        self.assertEqual(product.with_context(warehouse_id=second.id).qty_available,2)
        invoice=sale._create_invoices();self.assertEqual(invoice.state,'draft');invoice.action_post()
        self.assertEqual(invoice.amount_total,50)
        purchase.action_create_invoice();bill=purchase.invoice_ids;bill.invoice_date=fields.Date.today();bill.action_post()
        self.assertEqual(bill.amount_total,120)
        self.assertAlmostEqual(sum(invoice.line_ids.mapped('balance')),0)
        self.assertAlmostEqual(sum(bill.line_ids.mapped('balance')),0)
        self.env.flush_all()
        rows=self.env['ap.stock.overview'].search([('product_id','=',product.id)])
        self.assertEqual(sum(rows.mapped('quantity')),8)
        self.assertEqual(len(rows),2)
        with self.assertRaises(AccessError):
            # The SQL view is read-only through ACLs; no quantities may be fabricated by a report edit.
            rows.with_user(self.env.user).write({'quantity':100})
