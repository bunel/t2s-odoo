{
    "name" : "Diginesis Invoice",
    "version" : "0",
    "author" : "SC Diginesis SRL",
    "website" : "http://www.diginesis.com",
    "category" : "Generic Modules/Company",
    "description": """
This module contains:
	- Changes to Invoice Print.
""",
    "depends" : ["base", "account", "l10n_ro"],
    "init_xml" : [],
    "data" : [ "security/security.xml",
			 	"security/ir.model.access.csv",			 	
			 	"data/paperformat.xml",			 	
			 	"data/account_functionality.xml",
			 	"wizard/invoice_change_currency_view.xml",
			 	"wizard/invoice_allocation_view.xml",
			 	"views/account_move_views.xml",
			 	"views/report_invoice.xml",		 	
			 	"views/res_config_settings_views.xml",
			 	"views/report_partnerbankstatement.xml",
			 	"views/report.xml",
			 	"views/account_account_views.xml",
			 	"views/account_group_views.xml",
			 	"wizard/partner_bank_statement_view.xml",
			 	"wizard/account_move_reversal_view.xml",
			 ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}