# -*- coding: utf-8 -*-
from odoo import fields, models, _
import unicodedata

class DiginesisDeliveryCarrierRule(models.Model):
	_name = "diginesis.delivery.carrier.rule"
	_description = "Default Carrier Selection Rule"		
	
	_order="sequence"
	
	def _get_start_model(self):		
		for record in self:
			if record.type in ['partner_id.state_id.name', 'partner_id.city']:
				record.start_model = 'res.partner'
	
	name = fields.Char(string='Name', size=128)
	
	sequence = fields.Integer(string='Sequence')		
	type = fields.Selection([('partner_id.state_id.name','State'),('partner_id.city','City')], string='Type')
	start_model = fields.Char(compute='_get_start_model', store=False, readonly=True)
	
	value = fields.Char(string='Value', size=128)
	carrier_id = fields.Many2one(comodel_name='diginesis.delivery.carrier', string='Courier', required=True)
	
	destination_field = fields.Selection([('courier_id','Carrier'),('zip','Zip')], string='Destination Field', default="courier_id")
	destination_value = fields.Char(string='Zip', size=200)		
		
	def get_value(self, source_vals, destination_field, rule_domain=None):	
		def clean_text(val):
			if not val:
				return val
			
			val = val.strip().lower()			
			return ''.join(c for c in unicodedata.normalize('NFD', val) if unicodedata.category(c) != 'Mn')	
		
		destination_value = None
		#domain = [('destination_field', '=', destination_field)]
		domain = []
		if rule_domain:
			domain = domain + rule_domain
		for rule in self.env['diginesis.delivery.carrier.rule'].search(domain):
			if rule.type and rule.start_model and rule.value:
				attrs = rule.type.split('.')
				if not (attrs and len(attrs) > 0):
					continue
				current_obj = False
				if attrs[0] in source_vals:
					current_objs = self.env[rule.start_model].search([('id', '=', source_vals[attrs[0]])])
					if not (current_objs and len(current_objs) > 0):
						continue
					current_obj = current_objs[0]
									
				for attr in attrs[1:]:
					if current_obj and not getattr(current_obj, attr) is None:
						current_obj = getattr(current_obj, attr)
				if clean_text(current_obj) == clean_text(rule.value):
					destination_value = rule._get_value_by_field(destination_field)
					break
			else:
				destination_value = rule._get_value_by_field(destination_field)
				break
			
		return destination_value
	
	def _get_value_by_field(self, destination_field):
		for rule in self:
			return destination_field in ['courier_id'] and rule.carrier_id.id or rule.destination_value
		