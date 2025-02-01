# -*- coding: utf-8 -*-
from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    stock_packaging_foil_coefficient = fields.Float(related="company_id.stock_packaging_foil_coefficient", readonly=False,)
