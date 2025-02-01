# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare
from odoo.exceptions import UserError

class StockPicking(models.Model):
	_inherit = 'stock.picking'
	
	def do_invoice_for_picking(self):
		res = super(StockPicking, self).do_invoice_for_picking()
		
		Repair = self.env['repair.order']
		
		repairs = Repair.search([('picking_id', 'in', self.ids)])
		repairs.action_repair_invoice_create()

		invoice_dict = {}
		for repair in repairs.filtered(lambda x: x.picking_id and x.invoice_id):
			repair.picking_id.set_client_invoice(repair.invoice_id.id)
			invoice_dict.update({repair.picking_id.id: repair.invoice_id})
				
		res.update(invoice_dict)		
		return res