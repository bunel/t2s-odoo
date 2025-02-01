{
    "name" : "Diginesis Endpoint",
    "version" : "0",
    "author" : "SC Diginesis SRL",
    "website" : "http://www.diginesis.com",
    "category" : "Generic Modules/Company",
    "description": """
Creates Diginesis Api Endpoint object.
""",
    "depends" : ["base", "sale"],
    "init_xml" : [],
    "data" : ["security/ir.model.access.csv", 
			"views/diginesis_api_endpoint_view.xml"],
    "demo_xml" : [],
    "active": False,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}