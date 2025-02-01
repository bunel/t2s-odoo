from odoo import api, fields, models, tools, _
from datetime import datetime
from odoo.exceptions import ValidationError, UserError


class Company(models.Model):
    _name = 'res.company'
    _inherit = 'res.company'
    
    stock_packaging_foil_coefficient = fields.Float(string="Foil Coefficient", default=0.2, help="Packaging Foil Coefficient")