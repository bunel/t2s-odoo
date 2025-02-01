# -*- coding: utf-8 -*-
{
    'name': "Diginesis Warranty",

    'summary': """
        Warranty implementation""",

    'description': """
			Module implements:
			 - Serial Number object
			 - Serial Number and Warranty Period columns on Invoice Line
    """,

    'author': "SC Diginesis SRL",
    'website': "http://www.diginesis.com",

    # for the full list
    'category': 'Uncategorized',
    'version': '0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'product'],
    #'depends': ['base', 'diginesis_account', 'mrp', 'repair'],

    # always loaded
    'data': [
		"security/ir.model.access.csv",
		"views/serial_number_view.xml",
        "views/account_move_view.xml",        
        "views/product_views.xml",        
        "views/report_warrantycertificate.xml",        
        "views/report.xml",        
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
    'license': 'LGPL-3',
}