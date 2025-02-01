# -*- coding: utf-8 -*-
from odoo import models, fields, _

class DiginesisApiEndpoint(models.Model):	
	_inherit = "diginesis.api.endpoint"
	
	import_slip = fields.Boolean('Import Slip')		
	page_setup = fields.Selection([('A4', 'A4'), ('A5', 'A5'), ('A6', 'A6')], string="Page Setup", default='A4')