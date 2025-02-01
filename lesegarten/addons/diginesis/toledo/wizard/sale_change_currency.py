# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.tools import float_round, float_is_zero

class SaleChangeCurrency(models.TransientModel):
	_name = 'sale.change.currency'
	_description = 'Change Currency'

	def change_currency(self):
		self.ensure_one()
		
		if not self.env.company.company_currency_pricelist:
			raise UserError(_('Default Pricelist in Company Currency is not properly configured'))

		if not self.env.context.get('active_id'):
			raise UserError(_('Invalid quotation'))

		pricelist_id = self.env.company.company_currency_pricelist
		sale = self.env['sale.order'].browse(self.env.context['active_id'])

		self.update_prices(sale, pricelist_id)

		return {'type': 'ir.actions.act_window_close'}

	def update_prices(self, sale, new_pricelist):
		old_pricelist = sale.pricelist_id

		sale.write({'pricelist_id': new_pricelist.id})
		sale.message_post(
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

		lines_to_update = []
		for line in sale.order_line.filtered(lambda line: not line.display_type):
			lines_to_update.append((1, line.id, {'price_unit': (line.price_unit or 0) / old_currency_rate}))
		sale.update({'order_line': lines_to_update})

		return True
