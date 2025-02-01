# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, Warning


class AccountMove(models.Model):
	_inherit = 'account.move'

	amount_transport = fields.Monetary(string='Transport Amount', store=True, tracking=True,
										compute='_compute_transport_amount', currency_field='company_currency_id')

	@api.depends('line_ids.transport_subtotal')
	def _compute_transport_amount(self):
		for move in self:
			move.amount_transport = sum([val for val in move.mapped('line_ids.transport_subtotal') if val])

	def action_print_nir(self):
		if not self:
			return False

		pickings = self.env['stock.picking'].search([('vendorbill_id', 'in', self.ids), ('state', '=', 'done')])
		return pickings.action_print_transfer()


class AccountMoveLine(models.Model):
	_inherit = 'account.move.line'

	transport_subtotal = fields.Monetary(string='Transport', currency_field='company_currency_id')
	
