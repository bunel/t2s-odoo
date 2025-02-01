# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo.tools.misc import get_lang
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, float_round
import math

class SaleOrderLine(models.Model):
	_inherit = 'sale.order.line'

	max_discount = fields.Float(string="Max Discount (%)", default=0.0)
	
	@api.onchange('discount')
	def discount_change(self):
		user_is_manager = self.env.user.has_group('sales_team.group_sale_manager')
		for line in self:
			if line.discount > line.max_discount and not user_is_manager:
				line.discount = 0.0

	@api.onchange('product_id')
	def product_id_change(self):
		res = super().product_id_change()
				
		self._compute_max_discount()
				
		return res		
	
	@api.onchange('product_uom', 'product_uom_qty')
	def product_uom_change(self):
		res = super().product_uom_change()
		
		self._compute_max_discount()
		
		return res
	
	def _compute_max_discount(self):
		for line in self:
			max_discount = 0
			if line.price_unit and line.product_id:
				product_category = line.product_id.categ_id
				max_addition = product_category and product_category.max_addition or 0
				min_addition = product_category and product_category.min_addition or 0
								
				max_discount = (100 + max_addition) and math.floor(( (100*(max_addition - min_addition) / (100 + max_addition))) * 100) / 100 or 0	
				if max_discount < 0:
					max_discount = 0	
			
			line.max_discount = max_discount