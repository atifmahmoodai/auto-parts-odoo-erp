{
    'name': 'Auto Parts Dealer Operations',
    'summary': 'Company-scoped parts catalog, reviewed migration and location stock reporting',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Inventory',
    'author': 'Atif Mahmood',
    'license': 'LGPL-3',
    'depends': ['sale_management', 'sale_stock', 'purchase_stock', 'stock_account', 'crm'],
    'data': ['security/security.xml', 'security/ir.model.access.csv', 'views/product_views.xml',
             'views/import_views.xml', 'views/stock_views.xml', 'views/menus.xml'],
    'application': True,
    'installable': True,
}
