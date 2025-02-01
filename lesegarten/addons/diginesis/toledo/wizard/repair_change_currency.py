# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.tools import float_round, float_is_zero

class RepairChangeCurrency(models.TransientModel):
	_name = 'repair.change.currency'
	_description = 'Change Currency'

	def change_currency(self):
		self.ensure_one()
		
		if not self.env.company.company_currency_pricelist:
			raise UserError(_('Default Pricelist in Company Currency is not properly configured'))

		if not self.env.context.get('active_id'):
			raise UserError(_('Invalid repair order'))

		pricelist_id = self.env.company.company_currency_pricelist
		repair = self.env['repair.order'].browse(self.env.context['active_id'])

		self.update_prices(repair, pricelist_id)

		return {'type': 'ir.actions.act_window_close'}

	def update_prices(self, repair, new_pricelist):
		old_pricelist = repair.pricelist_id

		repair.write({'pricelist_id': new_pricelist.id})
		repair.message_post(
			body=_("Currency updated to company currency. Product prices have been recomputed accordingly."))

		old_currency = old_pricelist and old_pricelist.currency_id or False
		if not old_currency:
			return True

		new_currency = new_pricelist.currency_id
		if old_currency.id == new_currency.id:
			return True

		old_currency_rate = old_currency.rate
		if float_is_zero(old_currency_rate, precision_rounding=old_currency.rounding):
			return True

		operations_to_update = []
		for line in repair.operations.filtered(lambda line: line.type != 'remove'):
			operations_to_update.append((1, line.id, {'price_unit': (line.price_unit or 0) / old_currency_rate}))

		fees_to_update = []
		for line in repair.fees_lines:
			fees_to_update.append((1, line.id, {'price_unit': (line.price_unit or 0) / old_currency_rate}))

		repair.update({'operations': operations_to_update,
					   'fees_lines': fees_to_update})

		return True
