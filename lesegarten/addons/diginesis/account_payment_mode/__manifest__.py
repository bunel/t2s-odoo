{
    "name" : "Account Payment Mode",
    "version" : "15.1.0",
    "author" : "SC Diginesis SRL",
    "website" : "http://www.diginesis.com",
    "category" : "Financial Management/Configuration",
    "description": """
	- Defines Account Payment Mode model
""",
    "depends" : ["base", "account", "sale"],
    "init_xml" : [],
    "data" : [
					"security/security.xml",
					"security/ir.model.access.csv",
					"data/data.xml",
					"views/account_payment_mode_views.xml",
					"views/res_partner_view.xml",
					"views/account_move_views.xml",
					"views/sale_order_views.xml",
                    ],
    "demo_xml" : [],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
