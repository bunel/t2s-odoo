{
    "name" : "Toledo",
    "version" : "0",
    "author" : "SC Diginesis SRL",
    "website" : "http://www.diginesis.com",
    "category" : "Generic Modules/Company",
    "description": """
Diginesis implementation for Toledo 
""",
    "depends": ["base", "product", "account", "sales_team", "sale", 'l10n_ro', 'purchase',
                'diginesis_invoice', 'repair', 'stock', 'diginesis_warranty_repair', 'barcodes', 'diginesis_warranty', 'stock_account',
                'sale_workflow'],
    "init_xml": [],
    "data": ["security/security.xml",
			 "security/ir.model.access.csv",
			 "views/product_views.xml",
			 "views/report_invoice.xml",
			 "views/report_conformitycertificate.xml",
			 "views/report.xml",
             "wizard/sale_change_currency_view.xml",
             "wizard/repair_change_currency_view.xml",
			 "views/sale_views.xml",
			 "views/sale_report_templates.xml",
			 "views/res_config_settings_views.xml",
			 "views/res_currency_view.xml",
			 "views/purchase_views.xml",
			 "views/repair_view.xml",
			 "views/account_move_views.xml",
			 "views/stock_picking_views.xml",
			 "report/repair_templates_repair_order.xml",
			 "report/repair_label.xml",
			 "views/stock_valuation_layer_views.xml",
			 "views/product_pricelist_views.xml",
	],
    'assets': {
        'web.assets_backend': [

        ],
        'web.assets_qweb': [

        ],
    },
    "demo_xml" : [],
    "active": False,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}