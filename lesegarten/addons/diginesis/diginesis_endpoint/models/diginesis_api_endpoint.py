# -*- coding: utf-8 -*-
from odoo import fields, models, _

class DiginesisApiEndpoint(models.Model):	
	_name = "diginesis.api.endpoint"
	_description = "External Api Endpoint Credentials"
	
	name = fields.Char('Name', required=True)
	username = fields.Char('Username', required=True)
	password = fields.Char('Password', required=True)
	clientid = fields.Char('ClientId', required=True)
	endpoint = fields.Char('Endpoint', required=True)
	endpoint_lines = fields.One2many('diginesis.api.endpoint.line', 'endpoint_credentials_id', 'Endpoints')		
	
class DiginesisApiEndpointLine(models.Model):	
	_name = 'diginesis.api.endpoint.line'
	_description = 'External Api Endpoint Lines'
	
	endpoint_credentials_id = fields.Many2one('diginesis.api.endpoint', string='Endpoint Credentials', ondelete="cascade")
	name = fields.Char('Name', required=True)
	endpoint = fields.Char('Endpoint', required=True)
