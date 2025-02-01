# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import UserError

class AccountMove(models.Model):
	_name = "account.move"
	_inherit = "account.move"
	
	@api.model_create_multi
	def create(self, values):
		
		res = super(AccountMove, self).create(values)
		
		serial_number_values = []
		for invoice_line in res.filtered(lambda x: x.move_type in ['out_invoice', 'out_refund']).mapped('invoice_line_ids').filtered(lambda x: x.product_id and x.serial_number_id):
			serial_number_values.append({'product_id': invoice_line.product_id, 'serial_number': invoice_line.serial_number_id})
			
		if serial_number_values:				
			self._validate_serialnumbers(serial_number_values)
			
		return res
		
	def write(self, values):
			
		res = super(AccountMove, self).write(values)
		
		serial_number_values = []
		for invoice_line in self.filtered(lambda x: x.move_type in ['out_invoice', 'out_refund']).mapped('invoice_line_ids').filtered(lambda x: x.product_id and x.serial_number_id):
			serial_number_values.append({'product_id': invoice_line.product_id, 'serial_number': invoice_line.serial_number_id})
			
		if serial_number_values:				
			self._validate_serialnumbers(serial_number_values)
			
		return res
	
	def _post(self, soft=True):
		
		self._check_serialnumber()
		
		res = super(AccountMove, self)._post(soft=soft)
		
		self._use_serialnumber()
		
		return res
	
	def button_cancel(self):
		res = super(AccountMove, self).button_cancel()
		self._unuse_serialnumber()
		return res
	
	def _check_serialnumber(self):
		self.filtered(lambda x: x.move_type in ['out_invoice', 'out_refund']).mapped('invoice_line_ids').filtered(lambda x: x.quantity != 0)._check_serialnumber()
		
	def _validate_serialnumbers(self, values):
		res = dict((x['serial_number'], {}) for x in values if x.get('serial_number'))
		for v in values:
			serial_number = v.get('serial_number') or False
			product = v.get('product_id') or False
			if product and serial_number:
				res[serial_number].setdefault(product, 0)				
				res[serial_number][product] += 1
				
				if res[serial_number][product] > 1:
					raise UserError(_("It is not possible to invoice the same serial number multiple times."))
			
	def _use_serialnumber(self):
		self.mapped('invoice_line_ids').filtered(lambda x: (x.move_id.move_type in ['out_invoice'] and x.quantity > 0) or \
													(x.move_id.move_type in ['out_refund'] and x.quantity < 0))._use_serialnumber()
		self.mapped('invoice_line_ids').filtered(lambda x: (x.move_id.move_type in ['out_refund'] and x.quantity > 0) or \
													(x.move_id.move_type in ['out_invoice'] and x.quantity < 0))._use_refund_serialnumber()
			
	def _unuse_serialnumber(self):
				
		self.mapped('invoice_line_ids').filtered(lambda x: (x.move_id.move_type in ['out_invoice'] and x.quantity > 0) or \
													(x.move_id.move_type in ['out_refund'] and x.quantity < 0))._unuse_serialnumber()
		self.mapped('invoice_line_ids').filtered(lambda x: (x.move_id.move_type in ['out_refund'] and x.quantity > 0) or \
													(x.move_id.move_type in ['out_invoice'] and x.quantity < 0))._unuse_refund_serialnumber()
	
class AccountMoveLine(models.Model):
	_inherit = "account.move.line"

	serial_number_id = fields.Many2one('serial.number', string='Serial Number', copy=False)
	warranty = fields.Float('Warranty Period', help="Warranty period in months")
	
	@api.onchange('serial_number_id')
	def onchange_serial_number(self):
		warning_message = []
		if self.serial_number_id:			
			if self.serial_number_id.state == 'sold':
				warning_message.append(_("Serial number {0} has already been invoiced").format(self.serial_number_id.name))
				self.serial_number_id = False
				
			if self.product_id and self.serial_number_id.product_id.id != self.product_id.id:
				warning_message.append(_("Serial number cannot be used for this product"))
			
		if warning_message: 
			return {'warning': {'title': _('Warning'), 'message': "\n".join(warning_message)}}
	
	@api.onchange('product_id')
	def onchange_warranty_product_id(self):
		self.warranty = self.product_id and self.product_id.warranty or False
		
	def _get_warranty_expiration(self):
		self.ensure_one()
		
		date_invoice = self.move_id and self.move_id.invoice_date or False
		warranty = self.warranty or 0
		return date_invoice and warranty and date_invoice + relativedelta(months=int(warranty)) or False
	
	def _check_serialnumber(self):
		
		errors = []
		for line in self.filtered(lambda x: x.serial_number_id and x.serial_number_id.state == 'sold' and x.product_id):
			invoices = self.search([('serial_number_id', '=', line.serial_number_id.id), ('id', '!=', line.id)]).mapped('move_id')
			if invoices:
				tmp = ", ".join([inv.number or _('Draft') for inv in invoices])
				errors.append(_("Product {0} with serial number {1} is already invoiced on invoice {2}").format(line.product_id.display_name or line.name or '', line.serial_number_id.name or '', tmp))
		
		if self.filtered(lambda x: not x.product_id and x.serial_number_id):
			errors.append(_("It is not possible to use a serial number without selecting a product."))
			
		if errors:
			raise UserError("\n".join(errors))
	
	def _use_serialnumber(self):
		
		self._check_serialnumber()
		
		for line in self.filtered(lambda x: x.serial_number_id):				
			warranty_expiration = line._get_warranty_expiration()
			
			line.serial_number_id.write({'partner_id': line.partner_id and line.partner_id.id or False,
										'warranty': line.warranty or 0,
										'warranty_expiration_date': line._get_warranty_expiration(),
										'invoice_date': line.move_id and line.move_id.invoice_date or False,
										'state': 'sold',									
										})
		return True
	
	def _use_refund_serialnumber(self):
		
		self._check_serialnumber()
		
		for line in self.filtered(lambda x: x.serial_number_id):
			line.serial_number_id.write({'partner_id': line.partner_id and line.partner_id.id or False,
										'state': 'available',
										})
		return True
	
	def _unuse_serialnumber(self):
		return self.mapped('serial_number_id').write({'state': 'available'})
	
	def _unuse_refund_serialnumber(self):
		return self.mapped('serial_number_id').write({'state': 'sold'})
	