{
    "name" : "Toledo Enterprise",
    "version" : "0",
    "author" : "SC Diginesis SRL",
    "website" : "http://www.diginesis.com",
    "category" : "Generic Modules/Company",
    "description": """
Diginesis implementation for Toledo Enterprise
""",
    "depends" : ["account_accountant", 'barcodes_mobile', 'web_mobile', 'toledo'],
    "init_xml" : [],
    "data" : ["security/security.xml", 
			 "security/ir.model.access.csv",
			 ],
    "demo_xml" : [],
    "active": False,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'toledo_enterprise/static/src/js/*.js',
        ],
        'web.assets_qweb': [
            'toledo_enterprise/static/src/xml/**/*',
        ],
    }
}