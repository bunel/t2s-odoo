{
    "name" : "Localization Year",
    "version": "15.0.1.1.0",
    "author" : "SC Diginesis SRL",
    "website" : "http://www.diginesis.com",
    "category" : "Accounting/Localization",
    'summary': 'Define Year',
    "depends" : ["base", "account"],
    "init_xml" : [],
    "data" : [
                "security/security.xml",
                "security/ir.model.access.csv",
                "views/year_view.xml"
            ],
    "demo_xml" : [],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
