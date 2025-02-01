# -*- coding: utf-8 -*-
from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
	_inherit = 'res.config.settings'
	
	transport_account_id = fields.Many2one('account.account', related="company_id.transport_account_id", readonly=False)