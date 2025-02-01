{
    "name" : "Romania - Account Notice",
    "version" : "0",
    "author" : "SC Diginesis SRL",
    "website" : "http://www.diginesis.com",
    "category" : "Accounting/Accounting",
    "description": """
	- Account Notice (on Reception or on Delivery)
	- Method of working with the notice (choose one per partner):
	    - Receipt with notice (then invoice)
        - Receipt with invoice (without notice)
        - Invoice Goods in progress, notice and receipt
    - Partner configuration: 'Reception Mode'
""",
    "depends" : ["base", "stock", "account", "l10n_ro", "account_accountant"],
    "init_xml" : [],
    "data" : [
                "security/security.xml",
                "security/ir.model.access.csv",
                "data/data.xml",
                "wizard/notice_change_currency_view.xml",
                "views/notice_views.xml",
                "views/stock_picking_view.xml",
                "views/res_config_settings_views.xml",
                "views/report_accountnotice.xml",
                "views/report.xml",
                ],
    "demo_xml" : [],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
