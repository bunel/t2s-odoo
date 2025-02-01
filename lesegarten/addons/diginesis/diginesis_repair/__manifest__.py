{
    'name': 'Diginesis Repair',
    'version': '1.0',
    'summary': """
        Repair implementation""",
    'description': """
""",
    'author': 'SC Diginesis SRL',
    'website': 'http://www.diginesis.com',
    'depends': ['repair', 'stock', 'account', 'stock_account'],
    'data': [
			"security/ir.model.access.csv",
			"data/data.xml",
			"views/repair_view.xml",
			"views/res_config_settings_views.xml",
			"report/repair_templates_repair_order.xml",
			"data/paperformat.xml",
			"report/repair_reports.xml",
    ],
    'installable': True,
    'active': False,
    'license': 'LGPL-3',
}