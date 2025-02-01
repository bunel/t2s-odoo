# -*- coding: utf-8 -*-
from odoo import fields, api, models, _


class ProductPallet(models.Model):
    _name = 'product.pallet'
    _description = 'Product Pallet'
    _order = "name asc"

    name = fields.Char('Name', required=True)
    weight = fields.Float('Weight', digits=(5,2), required=True, help="Packaging weight in kg")
    

