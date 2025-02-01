{
    "name" : "Procurement Workflow",
    "version" : "0",
    "author" : "SC Diginesis SRL",
    "website" : "http://www.diginesis.com",
    "category" : "Inventory/Purchase",
    "description": """
	- Procurement workflow (choose one per partner):
	    - Receipt with notice (then invoice)
        - Receipt with invoice (without notice)
        - Invoice Goods in progress, notice and receipt
    - Partner configuration: 'Reception Mode'
""",
    "depends" : ["base", "account", "purchase", "stock", "account_notice", "purchase_stock", "diginesis_invoice", "l10n_ro_stock", "l10n_ro_stock_account", "vendor_bill_reference"],
    "init_xml" : [],
    "data" : [
                "security/security.xml",
                "security/ir.model.access.csv",
                "views/purchase_views.xml",
                "views/res_partner_views.xml",
                "views/notice_views.xml",
                "views/stock_picking_view.xml",
                "views/res_config_settings_views.xml",
                "views/account_move_view.xml",
                ],
    "demo_xml" : [],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
