# -*- coding: utf-8 -*-
{
    'name': "Diginesis Warranty Repair",

    'summary': """
        Warranty for Repairs implementation""",

    'description': """
			Module implements:
			 - Serial Number column on Repair
    """,

    'author': "SC Diginesis SRL",
    'website': "http://www.diginesis.com",

    # Categories can be used to filter modules in modules listing
    # for the full list
    'category': 'Uncategorized',
    'version': '0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'repair', 'diginesis_warranty'],

    # always loaded
    'data': [
		"security/ir.model.access.csv",
		"views/repair_view.xml",
		"views/serial_number_view.xml",
		"report/repair_templates_repair_order.xml",
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
    'license': 'LGPL-3',
}