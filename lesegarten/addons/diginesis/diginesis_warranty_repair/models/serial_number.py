# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class SerialNumber(models.Model):
	_name = "serial.number"
	_inherit = "serial.number"
	
	def action_view_repairs(self):		
		action = self.env['ir.actions.act_window']._for_xml_id('repair.action_repair_order_tree')
		action['domain'] = [('serial_number_id', 'in', self.ids)]		
		return action