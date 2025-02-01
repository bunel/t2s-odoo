# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from ast import literal_eval
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import float_compare, float_round


class ProductProduct(models.Model):
	_inherit = 'product.product'

	def action_view_stock_valuation_layers(self):

		domain = [('product_id', 'in', self.ids)]
		action = self.env["ir.actions.actions"]._for_xml_id("stock_account.stock_valuation_layer_action")
		context = {}
		context.update(self.env.context)
		context['no_at_date'] = True
		return dict(action, domain=domain, context=context)


class ProductCategory(models.Model):
	_inherit = "product.category"
	
	max_addition = fields.Float(string="Addition (%)")
	min_addition = fields.Float(string="Minimum Addition (%)")
	has_technical_description= fields.Boolean(string="Technical Description")

