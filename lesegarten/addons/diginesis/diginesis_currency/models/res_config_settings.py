# -*- coding: utf-8 -*-
from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
	_inherit = 'res.config.settings'
	
	currency_update_main_currency_name = fields.Char('Main Currency Name', related="company_id.currency_update_main_currency_name", readonly=False, help="Currency name as it appears in imported")
	currency_update_endpoint = fields.Char('XML Endpoint', related="company_id.currency_update_endpoint", readonly=False, help="Url")