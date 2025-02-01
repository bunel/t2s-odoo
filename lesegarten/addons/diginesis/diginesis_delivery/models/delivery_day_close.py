# -*- coding: utf-8 -*-
from odoo import fields, models, _

class DiginesisDeliveryDayClose(models.Model):
	_name = "diginesis.delivery.day.close"
	_description = "General Day Close Entity"		
	
	name = fields.Char(string='Name', size=128)
	
	state = fields.Selection([('draft','Draft'),('closed','Closed'),('with_manifest', 'With Manifest')],string='State', default='draft')		
	message = fields.Text(string='Message', readonly=True)
	
	awb_date = fields.Datetime(string='AWB Date', required=True)
	carrier_id = fields.Many2one(comodel_name='diginesis.delivery.carrier', string='Carrier', required=True)
	carrier_name = fields.Char(related = 'carrier_id.name',readonly=True,string='Carrier')
	awbs = fields.Text(string='Related Deliveries', readonly=True)	
	
	def action_close(self):				
		self._manage_action(action='close')
				
	def action_print(self):
		self._manage_action(action='reprint')
				
	def _manage_action(self, action='close'):
		for day_close in self:
			if not (day_close.carrier_id and day_close.carrier_id.id):
				raise UserError(_('Please select a Carrier!'))
			
			self.env.cr.execute("SELECT id, code FROM diginesis_delivery_carrier WHERE code=%s LIMIT 1", (day_close.carrier_id.code,))
			delivery_carrier = self.env.cr.fetchone()		
			if delivery_carrier:
				custom_model = 'diginesis.delivery.%s' % delivery_carrier[1]
				custom_delivery_obj = self.env[custom_model]
				if custom_delivery_obj is None:
					raise UserError(_('Invalid carrier %s' % custom_model))
				
				res = custom_delivery_obj.close_delivery_day({'parent_id': day_close.id, 'parent_model': self._name, 'awb_date': day_close.awb_date, 'action': action})
				
				state = 'draft'
				if res.get('state', False):
					if res['state'] in ['closed']:
						state = 'closed'
					elif res['state'] in ['printed']:
						state = 'with_manifest'
				
				vals = {'message': res.get('warning', False), 'state': state, 'awbs': res.get('awbs', False) }
				day_close.write(vals)
		