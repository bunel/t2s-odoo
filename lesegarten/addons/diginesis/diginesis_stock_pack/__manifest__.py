# -*- coding: utf-8 -*-

{
    'name': 'Diginesis Stock Pack',
    'version': '1.0',    
    "author" : "SC Diginesis SRL",
    "website" : "http://www.diginesis.com",
    "category" : "Generic Modules/Stock",
    'summary': '',
    'description' : """
Packing / unpacking with defining the types of packages and pallets.\n		
Features:
	- Environment Reception Report
	- Environment Delivery Report
    """,
    'depends': ['base','stock', 'product', 'account_reports', 'l10n_ro_config'],
    'category': '',
    'sequence': 10,
    'demo': [],
    'data': [
		"security/ir.model.access.csv",
		"data/data.xml",
		"wizard/add_picking_tracking_views.xml",
		"views/product_pack_views.xml",
		"views/product_pallet_views.xml",
		"views/stock_tracking_views.xml",
		"views/stock_picking_view.xml",
		"views/res_config_settings_views.xml",
		"views/report_financial.xml",
		"views/search_template_view.xml",
		"report/environment_delivery_report_view.xml",
		"report/environment_reception_report_view.xml",
        ],
    'installable': True,
    'application': False,
    'auto_install': False,
}