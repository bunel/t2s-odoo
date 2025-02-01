# -*- coding: utf-8 -*-
from odoo import fields, api, models, _


class ProductPack(models.Model):
    _name = 'product.pack'
    _description = "Product Pack"
    _order = "name asc"
    
    name = fields.Char('Name', required=True)
    


