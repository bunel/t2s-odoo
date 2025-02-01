# -*- coding: utf-8 -*-
from odoo import fields, models

class Company(models.Model):
	_inherit = 'res.company'

	repair_delivery_picking_type = fields.Many2one('stock.picking.type', string='Repair Delivery Operation')
