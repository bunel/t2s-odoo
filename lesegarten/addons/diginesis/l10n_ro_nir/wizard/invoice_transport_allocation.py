# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools import float_round, float_is_zero
from odoo.exceptions import UserError

class InvoiceTransportAllocationWizard(models.TransientModel):
	_name = 'invoice.transport.allocation.wizard'
	_description = 'Invoice transport allocation'

	amount = fields.Float('Amount to Allocate', required=True, digits=0)
	
	def action_allocate(self):
		self = self[0]
		
		product_price_digits = self.env['decimal.precision'].precision_get('Product Price')
		
		invoice_ids = self.env.context.get('active_ids')
		if not invoice_ids:
			raise UserError(_("Invalid invoice"))
		
		if len(invoice_ids) > 1:
			invoice_ids = invoice_ids[0]
		
		invoice = self.env['account.move'].browse(invoice_ids).with_context(check_move_validity=False)
		tmp_to_rep = to_rep = self.amount

		invoice_lines = invoice.invoice_line_ids.filtered(lambda lin: lin.product_id and lin.product_id.type != 'service' and lin.price_subtotal).with_context(check_move_validity=False)
		total = sum([lin.price_subtotal for lin in invoice_lines if lin.price_subtotal])

		if float_is_zero(total, precision_digits=2):
			return {'type': 'ir.actions.act_window_close'}

		for line in invoice_lines:
			line_transport = float_round(line.price_subtotal * to_rep / total, precision_digits=product_price_digits)
			tmp_to_rep -= line_transport
			line.write({'transport_subtotal': line_transport})
		
		if not float_is_zero(tmp_to_rep, precision_digits=product_price_digits) and invoice_lines:
			last_line = invoice_lines[-1]
			last_line.write({'transport_subtotal': (last_line.transport_subtotal or 0) + tmp_to_rep})

		return {'type': 'ir.actions.act_window_close'}

