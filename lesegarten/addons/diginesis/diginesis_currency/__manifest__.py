{
    "name" : "Diginesis Currency",
    "version" : "0",
    "author" : "SC Diginesis SRL",
    "website" : "http://www.diginesis.com",
    "category" : "Financial Management/Configuration",
    "description": """
	- Import exchange rates from BNR http://www.bnr.ro
	- Display exchange rates expressed in company currency
	- Always convert currency at previous date from the asked date.
""",
    "depends" : ["base", "account"],
    "init_xml" : [],
    "data" : [
					"security/security.xml",
					"security/ir.model.access.csv",
					"data/cron_data.xml",
					"views/res_company_view.xml",
					"views/res_currency_view.xml",
					"views/res_config_settings_views.xml",
                    ],
    "demo_xml" : [],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
