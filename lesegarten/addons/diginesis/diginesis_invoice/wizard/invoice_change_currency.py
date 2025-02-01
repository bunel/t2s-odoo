# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class InvoiceChangeCurrency(models.TransientModel):
	_name = 'invoice.change.currency'
	_description = 'Change Currency'
	
	currency_id = fields.Many2one('res.currency', 'Change currency to', required=True)
	specify_rate = fields.Boolean(string='Specify Rate')
	custom_rate = fields.Float(string="Custom Rate", digits=(12, 12),)
	invoice_ids = fields.Many2many('account.move', default=lambda self: self.env.context.get('active_ids'))

	@api.onchange('invoice_ids')
	def onchange_invoices(self):
		res = {}
		if self.invoice_ids:
			invoice_in_other_currency = self.invoice_ids.filtered(lambda x: x.currency_id.id != x.company_id.currency_id.id)
			if invoice_in_other_currency:
				res['domain'] = {'currency_id': [('id', 'in', invoice_in_other_currency.mapped('company_id.currency_id').ids)]}

		return res

	def change_currency(self):
		self.ensure_one()
		
		new_currency = self.currency_id
		
		if not new_currency:
			raise UserError(_("Invalid currency"))
		
		invoice_ids = self.env.context.get('active_ids')
		if not invoice_ids:
			raise UserError(_("Invalid invoice"))
		
		invoices = self.env['account.move'].search([('id', 'in', invoice_ids), ('currency_id', '!=', new_currency.id)])
		if not invoices:
			raise UserError(_("Invoice currency already is {0}").format(new_currency.name or ''))

		invoices = invoices.with_context(check_move_validity=False)
		if self.specify_rate and self.custom_rate:
			self._change_with_custom_rate(invoices, new_currency, self.custom_rate)
		else:
			self._change_with_default_rate(invoices, new_currency)

		return {'type': 'ir.actions.act_window_close'}

	@api.model
	def _change_with_default_rate(self, invoices, new_currency):

		invoices = invoices.with_context(check_move_validity=False)
		for invoice in invoices:
			computed_rate = new_currency.with_context(date=invoice.invoice_date).rate
			invoice_currency_rate = invoice.currency_id.with_context(date=invoice.invoice_date).rate

			currencies = {'new_currency': new_currency.id,
						  'company_currency': invoice.company_id.currency_id.id,
						  'invoice_currency': invoice.currency_id.id}

			used_rate = 0.0
			invoice_lines = invoice.invoice_line_ids.with_context(check_move_validity=False)
			for line in invoice_lines:
				new_price = 0
				if currencies['company_currency'] == currencies['invoice_currency']:
					used_rate = computed_rate
					new_price = line.price_unit * used_rate
				else:
					if currencies['company_currency'] == currencies['new_currency']:
						used_rate = invoice_currency_rate
						if used_rate <= 0:
							raise UserError(_('Current currency is not properly configured'))
						new_price = line.price_unit / used_rate
					else:
						used_rate = computed_rate
						if invoice_currency_rate <= 0:
							raise UserError(_('Current currency is not properly configured'))
						new_price = (line.price_unit / invoice_currency_rate) * used_rate
				line.write({'price_unit': new_currency.round(new_price)})

			used_rate = 1 / used_rate if used_rate > 0 else used_rate
			invoice.write({'currency_id': new_currency.id, 'last_exchange_rate': used_rate, 'rate': 0.0})

			invoice_lines._onchange_mark_recompute_taxes()
			invoice._onchange_currency()
		return True

	@api.model
	def _change_with_custom_rate(self, invoices, new_currency, custom_rate):
		""" custom_rate is user input so it will be in 'human-readable' form regardless of the exchange direction
			(company currency -> new currency or new currency -> company currency)

			- if change from currency to company currency then use custom_rate
			- if change from company currency to currency then use 1/custom_rate
		"""

		invoices = invoices.with_context(check_move_validity=False)
		for invoice in invoices:

			currencies = {'new_currency': new_currency.id,
						  'company_currency': invoice.company_id.currency_id.id,
						  'invoice_currency': invoice.currency_id.id}

			computed_rate = 1 / custom_rate if (custom_rate > 0 and currencies['company_currency'] == currencies['invoice_currency']) else custom_rate

			invoice_lines = invoice.invoice_line_ids.with_context(check_move_validity=False)
			for line in invoice_lines:
				new_price = line.price_unit * computed_rate
				line.write({'price_unit': new_currency.round(new_price)})

			invoice.write({'currency_id': new_currency.id, 'last_exchange_rate': custom_rate, 'rate': 0.0})

			invoice_lines._onchange_mark_recompute_taxes()
			invoice._onchange_currency()
		return True
