# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools import float_round, float_is_zero
from odoo.exceptions import UserError

class InvoiceAllocationWizard(models.TransientModel):
	_name = 'invoice.allocation.wizard'
	_description = 'Invoice allocation'

	amount = fields.Float('Amount to Allocate', required=True, digits=0)
	
	def invoice_allocation(self):
		self = self[0]
		
		product_price_digits = self.env['decimal.precision'].precision_get('Product Price')
		
		invoice_ids = self.env.context.get('active_ids')
		if not invoice_ids:
			raise UserError(_("Invalid invoice"))
		
		if len(invoice_ids) > 1:
			invoice_ids = invoice_ids[0]
		
		invoice = self.env['account.move'].browse(invoice_ids).with_context(check_move_validity=False)
		to_rep = self.amount

		if float_is_zero(invoice.amount_untaxed, precision_digits=2):
			return {'type': 'ir.actions.act_window_close'}
		
		rounding_digits = invoice.currency_id.decimal_places
		total_old = invoice.amount_untaxed
		total_new = total_old + to_rep
		
		calc_amount = 0.0
		invoice_lines = invoice.invoice_line_ids.with_context(check_move_validity=False)
		for line in invoice_lines:
			new_price = float_round((line.price_unit * (1 + to_rep / total_old)), precision_digits=product_price_digits)
			calc_amount += invoice.currency_id.round(line.quantity * (new_price - new_price / 100 * line.discount))
			line.write({'price_unit': new_price})
		
		if not float_is_zero(total_new - calc_amount, precision_digits=rounding_digits):
			rest = invoice.currency_id.round(total_new - calc_amount)
			last_invoice_line = len(invoice_lines) > 0 and invoice_lines.filtered(lambda x: x.quantity != 0) or False
			should_add_difference_line = self.env.company.add_invoice_allocate_difference_line

			if last_invoice_line:
				last_invoice_line = last_invoice_line[-1]

			if should_add_difference_line:
				difference_line = {
					'name': _('Price Difference for allocated amount {0}').format(to_rep),
					'price_unit': rest,
					'quantity': 1,
					'product_uom_id': last_invoice_line and last_invoice_line.product_uom_id and last_invoice_line.product_uom_id.id or False,
					'product_id': False,
					'tax_ids': last_invoice_line and last_invoice_line.tax_ids and [(6, 0, last_invoice_line.tax_ids.ids)] or False
				}
				invoice.write({'invoice_line_ids': [(0, 0, difference_line)]})
			elif last_invoice_line:
				last_invoice_line.write({'price_unit': last_invoice_line.price_unit + (rest/last_invoice_line.quantity)})

		invoice = invoice.with_context(invoice_manually_rate=invoice.rate) if invoice.rate else invoice
		invoice._move_autocomplete_invoice_lines_values()
						
		return {'type': 'ir.actions.act_window_close'}

