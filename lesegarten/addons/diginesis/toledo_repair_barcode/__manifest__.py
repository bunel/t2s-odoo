# -*- coding: utf-8 -*-

{
    'name': "Toledo Repair Barcode",
    'summary': "Use barcode scanners to process repair operations",
    'description': """
This module enables the barcode scanning feature for the repair management system.
    """,
    'category': 'Inventory/Inventory',
    'version': '15.1.0',
    'depends': ['repair', 'toledo'],
    'data': [
        'security/ir.model.access.csv',
        'views/repair_barcode_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'toledo_repair_barcode/static/src/**/*.js',
            'toledo_repair_barcode/static/src/**/*.scss',
        ],
        'web.assets_qweb': [
            'toledo_repair_barcode/static/src/**/*.xml',
        ],
    }
}
