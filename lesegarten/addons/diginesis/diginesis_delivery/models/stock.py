# -*- coding: utf-8 -*-
import time

from odoo.tools.translate import _
from datetime import datetime, timedelta
from odoo import fields, models, _, SUPERUSER_ID
from odoo.exceptions import UserError

class StockPicking(models.Model):	
	_inherit = "stock.picking"
	
	courier_id = fields.Many2one("diginesis.delivery.carrier", string="Courier")
	
	
	def create(self, vals):		
		vals['courier_id'] = self.env['diginesis.delivery.carrier.rule'].get_value(vals, 'courier_id')
		return super(StockPicking, self).create(vals)
	
	def create_delivery(self):
		res = False
		for picking in self:
			self.env.cr.execute("SELECT id FROM diginesis_delivery WHERE stock_picking_id = %s", (picking.id,))
			delivery_ids = self.env.cr.fetchall()	
			if len(delivery_ids) > 0:
				return [x[0] for x in delivery_ids]
			
			courier_code = self.env.context.get('delivery_courier_code', False) or (picking.courier_id and picking.courier_id.code) or False
			if not courier_code:
				raise UserError(_('Please select a Courier!'))
			
			self.env.cr.execute("SELECT id, code FROM diginesis_delivery_carrier WHERE code=%s LIMIT 1", (courier_code,))
			delivery_carrier = self.env.cr.fetchone()		
			if delivery_carrier:
				custom_model = 'diginesis.delivery.%s' % delivery_carrier[1]		
				CustomDelivery = self.env[custom_model]
				if not hasattr(CustomDelivery, 'make_delivery'):
					raise UserError(_('Invalid carrier %s' % custom_model))
				
				vals = {
					'parent': picking,
					'parent_type': 'stock_picking',
				}
				
				res = CustomDelivery.make_delivery(vals)
				if res:
					return [res]
						
		return res

	def button_delivery(self):
		
		delivery_ids = self.create_delivery()
		if not delivery_ids:			
			raise UserError(_('Delivery cannot be created!'))
				
		delivery_vals = self.env['diginesis.delivery'].browse(delivery_ids).read(['res_id', 'res_model'])
		if len(delivery_vals) <= 0:			
			raise UserError(_('Delivery cannot be created!'))		
		
		res_model = delivery_vals[0]['res_model']
		if len(delivery_vals) > 1:			 
			ids = [x['res_id'] for x in delivery_vals]			
			return {
				'type': 'ir.actions.act_window',
				'view_mode': 'tree,form',
				'res_model': res_model,
				'domain':  [('id', 'in', ids)],
				'target': 'current',
				'context': {},
			}
		else:		
			return {
				'type': 'ir.actions.act_window',
				'view_mode': 'form',
				'res_model': res_model,
				'res_id': delivery_vals[0]['res_id'],
				'target': 'current',
				'context': {},
			}
		