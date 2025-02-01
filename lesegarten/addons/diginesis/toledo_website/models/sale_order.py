# -*- coding: utf-8 -*-
from odoo import api, models, fields, _
from odoo.exceptions import UserError, ValidationError

class SaleOrderLine(models.Model):
	_inherit = "sale.order.line"

	def get_description_following_lines(self):
		if self.product_id:
			return [self.product_id.description or '']
		
		return super().get_description_following_lines()