{
    "name" : "Sale Workflow",
    "version" : "0",
    "author" : "SC Diginesis SRL",
    "website" : "http://www.diginesis.com",
    "category" : "Inventory/Sale",
    "description": """
	Sale workflow
""",
    "depends" : ["base", "account", "sale", "stock", "sale_stock", "account_notice", "diginesis_invoice", "l10n_ro_stock", "product", "l10n_ro_stock_account"],
    "init_xml" : [],
    "data" : [
                "security/security.xml",
                "security/ir.model.access.csv",
                "data/data.xml",
                "views/notice_views.xml",
                "views/sale_views.xml",
                "views/stock_picking_view.xml",
                "views/res_config_settings_views.xml",
                "views/report_accountnotice.xml",
                ],
    "demo_xml" : [],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
