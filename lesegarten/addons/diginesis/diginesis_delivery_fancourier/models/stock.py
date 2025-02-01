# -*- coding: utf-8 -*-
from odoo import models, fields, _
	
class StockWarehouse(models.Model):
	_inherit = "stock.warehouse"
	
	fancourier_api_endpoint = fields.Many2one('diginesis.api.endpoint', string="Fan Courier Endpoint Credentials")
		