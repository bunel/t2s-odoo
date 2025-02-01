# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
{
    "name": "All in one Merge | Merge Sale Order | Merge Purchase Order | Merge MRP Order | Merge Invoice | Merge Inventory | Merge Internal Category With POS Category | Merge Internal Category With E-commerce Category",
    "author": "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "license": "OPL-1",
    "support": "support@softhealer.com",
    "category": "Extra Tools",
    "summary": "Merge Sales Order,Merge Quotation,Merge Request For Quotation,Merge MRP,Merge Bill,Merge Credit Note, Merge Debit Note,Merge Categories,Merge POS Category,Merge ecommerce Category,Merge Incoming Order,Merge Delivery Order Odoo",
    "description": """This module useful to merge sale orders/quotation, purchase order/request for quotation, incoming order/outgoing order/internal transfer, invoice/bill/credit note/debit note, manufacturing order, product internal category with the POS category & product internal category with the e-commerce category.""",
    "version": "15.0.3",
    "depends": [
        "website_sale", "sale_management", "stock", "purchase"
    ],
    "application": True,
    "data": [

        "sh_ecommerce_categories_merge/security/base_security.xml",
        "sh_ecommerce_categories_merge/security/ir.model.access.csv",
        "sh_ecommerce_categories_merge/views/website_config_settings.xml",
        "sh_ecommerce_categories_merge/views/view.xml",
        "sh_ecommerce_categories_merge/wizard/merge_category_wizard_view.xml",

        "sh_merge_invoice/security/ir.model.access.csv",
        "sh_merge_invoice/wizard/merge_invoice.xml",

        "sh_merge_picking_order/security/ir.model.access.csv",
        "sh_merge_picking_order/views/res_config_setting.xml",
        "sh_merge_picking_order/wizard/merge_picking_order.xml",

        "sh_merge_purchase_order/security/ir.model.access.csv",
        "sh_merge_purchase_order/wizard/merge_purchase_order.xml",

        "sh_merge_sale_order/security/ir.model.access.csv",
        "sh_merge_sale_order/wizard/merge_sale_order.xml",

    ],
    "images": ["static/description/background.png", ],
    "auto_install": False,
    "installable": True,
    "price": 90,
    "currency": "EUR"
}
