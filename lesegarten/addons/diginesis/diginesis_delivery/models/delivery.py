# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class DiginesisDeliveryCarrier(models.Model):
	_name = "diginesis.delivery.carrier"
	_description = "General Carrier Entity"	
	
	name = fields.Char('Name', size=64, help="Carrier Name", readonly=True)
	code = fields.Char('Code', size=64, readonly=True)
		

class DiginesisDelivery(models.Model):
	_name = "diginesis.delivery"
	_description = "General Carrier Entity"
	
	@api.depends('res_model', 'res_id')
	def _get_delivery_data(self):		
		for delivery in self:
			if delivery.res_model and delivery.res_id and self.env[delivery.res_model]:
				ResModel = self.env[self.res_model]							
				custom_delivery = ResModel.browse(delivery.res_id)
				
				delivery.awb = custom_delivery and getattr(custom_delivery, 'awb', False)
				delivery.state = custom_delivery and getattr(custom_delivery, 'state', False)
				delivery.carrier_name = custom_delivery and hasattr(custom_delivery, 'carrier_id') and custom_delivery.carrier_id and custom_delivery.carrier_id.name or False
			else:
				self.awb = False
				self.state = False 
				self.carrier_name = False
			
	create_date = fields.Datetime('Create Date', readonly=True)
	res_model = fields.Char('Related Delivery Model', size=128, required=True, readonly=True)
	res_id = fields.Integer('Related Delivery ID', required=True, readonly=True)
	stock_picking_id = fields.Many2one('stock.picking', 'Delivery', required=True)	
		
	awb = fields.Char(string="AWB", compute=_get_delivery_data, store=False)
	carrier_name = fields.Char(string="Carrier", compute=_get_delivery_data, store=False)
	state = fields.Char(string='State', compute=_get_delivery_data, store=False)
		
	def count_deliveries(self, carrier_code, stock_picking_ids):				
		self.env.cr.execute("""SELECT count(id) FROM diginesis_delivery WHERE stock_picking_id IN %s AND res_model=%s""", (tuple(stock_picking_ids), 'diginesis.delivery.%s' % carrier_code,))
		delivery_count = self.env.cr.fetchone()
		return len(delivery_count) > 0 and delivery_count[0] or 0
	
	def search_deliveries(self, carrier_code, stock_picking_ids):
		return self.search([('stock_picking_id', 'in', stock_picking_ids),('res_model', '=', 'diginesis.delivery.%s' % carrier_code)]).read(['res_id', 'res_model'])
		