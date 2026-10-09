from odoo import fields, models, tools


class PartsStockOverview(models.Model):
    _name = 'ap.stock.overview'
    _description = 'Auto Parts Internal Location Stock'
    _auto = False
    _rec_name = 'product_id'
    _order = 'product_id, location_id'

    product_id = fields.Many2one('product.product', readonly=True)
    location_id = fields.Many2one('stock.location', readonly=True)
    company_id = fields.Many2one('res.company', readonly=True)
    category_id = fields.Many2one('product.category', readonly=True)
    brand = fields.Char(readonly=True)
    quantity = fields.Float('On hand', readonly=True)
    reserved = fields.Float('Reserved', readonly=True)
    available = fields.Float('Unreserved', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute('''CREATE VIEW ap_stock_overview AS
            SELECT MIN(q.id) AS id, q.product_id, q.location_id, q.company_id,
                   t.categ_id AS category_id, t.ap_brand AS brand,
                   SUM(q.quantity) AS quantity, SUM(q.reserved_quantity) AS reserved,
                   SUM(q.quantity - q.reserved_quantity) AS available
              FROM stock_quant q JOIN stock_location l ON l.id=q.location_id
              JOIN product_product p ON p.id=q.product_id
              JOIN product_template t ON t.id=p.product_tmpl_id
             WHERE t.ap_is_part AND l.usage='internal' AND q.owner_id IS NULL
             GROUP BY q.product_id,q.location_id,q.company_id,t.categ_id,t.ap_brand''')
