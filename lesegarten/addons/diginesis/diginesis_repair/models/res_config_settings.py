# -*- coding: utf-8 -*-
from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
	_inherit = 'res.config.settings'
	
	repair_delivery_picking_type = fields.Many2one('stock.picking.type', related="company_id.repair_delivery_picking_type", readonly=False)