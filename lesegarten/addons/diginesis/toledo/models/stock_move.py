# -*- coding: utf-8 -*-
from odoo import api, fields, models, Command, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError


class StockMove(models.Model):
	_name = "stock.move"
	_inherit = "stock.move"

	def redo_svl(self):
		self.ensure_one()
		valued_moves = {valued_type: self.env['stock.move'] for valued_type in self._get_valued_types()}
		for valued_type in self._get_valued_types():
			if getattr(self, '_is_%s' % valued_type)():
				valued_moves[valued_type] |= self
		stock_valuation_layers = self.env['stock.valuation.layer'].sudo()
				# Create the valuation layers in batch by calling `moves._create_valued_type_svl`.
		for valued_type in self._get_valued_types():
			todo_valued_moves = valued_moves[valued_type]
			if todo_valued_moves:
				todo_valued_moves._sanity_check_for_valuation()
				stock_valuation_layers |= getattr(todo_valued_moves, '_create_%s_svl' % valued_type)()
				self.env.cr.commit()
		#update create_date pe svl si...
		#stock_valuation_layers._validate_accounting_entries()