# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime
from dateutil.relativedelta import relativedelta

class Repair(models.Model):
	_inherit = 'repair.order'

	serial_number_id = fields.Many2one('serial.number', 'Serial Number')
	
	@api.onchange('serial_number_id')
	def onchange_serial_number(self):
		res = {}
		if self.product_id and self.serial_number_id and self.serial_number_id.product_id:
			if self.product_id.id != self.serial_number_id.product_id.id:
				res['warning'] = {'title': _('Warning'), 'message': _('Repair Product does not match Serial Number Product!')}
			self.guarantee_limit = self.serial_number_id.warranty_expiration_date or False
		else:	
			self.guarantee_limit = False
		return res	
	
	@api.onchange('product_id')
	def onchange_product_id(self):
		res = super(Repair, self).onchange_product_id()
		
		self.serial_number_id = False
		return res