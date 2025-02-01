# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class NoticeChangeCurrency(models.TransientModel):
	_name = 'notice.change.currency'
	_description = 'Change Currency'
	
	currency_id = fields.Many2one('res.currency', 'Change currency to', required=True)
	specify_rate = fields.Boolean(string='Specify Rate')
	custom_rate = fields.Float(string="Custom Rate", digits=(12, 12),)
	notice_ids = fields.Many2many('account.notice', default=lambda self: self.env.context.get('active_ids'))

	@api.onchange('notice_ids')
	def onchange_notices(self):
		res = {}
		if self.notice_ids:
			in_other_currency = self.notice_ids.filtered(lambda x: x.currency_id.id != x.company_id.currency_id.id)
			if in_other_currency:
				res['domain'] = {'currency_id': [('id', 'in', in_other_currency.mapped('company_id.currency_id').ids)]}

		return res

	def change_currency(self):
		self.ensure_one()
		
		new_currency = self.currency_id
		
		if not new_currency:
			raise UserError(_("Invalid currency"))
		
		if not self.notice_ids:
			raise UserError(_("Invalid invoice"))
		
		notices = self.notice_ids.filtered(lambda x: not x.currency_id or x.currency_id != new_currency.id)
		if not notices:
			raise UserError(_("Notice currency already is {0}").format(new_currency.name or ''))

		if self.specify_rate and self.custom_rate:
			self._change_with_custom_rate(notices, new_currency, self.custom_rate)
		else:
			self._change_with_default_rate(notices, new_currency)

		return {'type': 'ir.actions.act_window_close'}

	@api.model
	def _change_with_default_rate(self, notices, new_currency):

		for notice in notices:
			computed_rate = new_currency.with_context(date=notice.date).rate
			notice_currency_rate = notice.currency_id.with_context(date=notice.date).rate

			currencies = {'new_currency': new_currency.id,
						  'company_currency': notice.company_id.currency_id.id,
						  'notice_currency': notice.currency_id.id}

			used_rate = 0.0
			notice_lines = notice.notice_line_ids
			for line in notice_lines:
				new_price = 0
				if currencies['company_currency'] == currencies['notice_currency']:
					used_rate = computed_rate
					new_price = line.price_unit * used_rate
				else:
					if currencies['company_currency'] == currencies['new_currency']:
						used_rate = notice_currency_rate
						if used_rate <= 0:
							raise UserError(_('Current currency is not properly configured'))
						new_price = line.price_unit / used_rate
					else:
						used_rate = computed_rate
						if notice_currency_rate <= 0:
							raise UserError(_('Current currency is not properly configured'))
						new_price = (line.price_unit / notice_currency_rate) * used_rate
				line.write({'price_unit': new_currency.round(new_price)})

			used_rate = 1 / used_rate if used_rate > 0 else used_rate
			notice.write({'currency_id': new_currency.id, 'last_exchange_rate': used_rate})

		return True

	@api.model
	def _change_with_custom_rate(self, notices, new_currency, custom_rate):
		""" custom_rate is user input so it will be in 'human-readable' form regardless of the exchange direction
			(company currency -> new currency or new currency -> company currency)

			- if change from currency to company currency then use custom_rate
			- if change from company currency to currency then use 1/custom_rate
		"""

		for notice in notices:

			currencies = {'new_currency': new_currency.id,
						  'company_currency': notice.company_id.currency_id.id,
						  'notice_currency': notice.currency_id.id}

			computed_rate = 1 / custom_rate if (custom_rate > 0 and currencies['company_currency'] == currencies['notice_currency']) else custom_rate

			for line in notice.notice_line_ids:
				new_price = line.price_unit * computed_rate
				line.write({'price_unit': new_currency.round(new_price)})

			notice.write({'currency_id': new_currency.id})

		return True
