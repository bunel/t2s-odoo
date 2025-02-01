{
    "name" : "Toledo Website",
    "version" : "0",
    "author" : "SC Diginesis SRL",
    "website" : "http://www.diginesis.com",
    "category" : "Generic Modules/Company",
    "description": """
Diginesis implementation for Toledo Website
""",
    "depends" : ["base", "website", "website_sale", "product"],
    "init_xml" : [],
    "data" : ["security/security.xml", 
			 "security/ir.model.access.csv",
			 "views/templates.xml",
			 ],
    "demo_xml" : [],
    "active": False,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}