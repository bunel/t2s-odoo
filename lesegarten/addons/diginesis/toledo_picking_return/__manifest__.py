{
    "name" : "Toledo Picking Return",
    "version" : "0",
    "author" : "SC Diginesis SRL",
    "website" : "http://www.diginesis.com",
    "category" : "Generic Modules/Company",
    "description": """
Compute unit price for OUT Return
""",
    "depends" : ["stock", "stock_account"],
    "init_xml" : [],
    "data" : ["security/security.xml", 
			 "security/ir.model.access.csv",
			 ],
    "demo_xml" : [],
    "active": False,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}