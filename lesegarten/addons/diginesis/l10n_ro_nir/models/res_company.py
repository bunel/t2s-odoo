# -*- coding: utf-8 -*-
from odoo import fields, models

class Company(models.Model):
	_inherit = 'res.company'

	transport_account_id = fields.Many2one('account.account', string="Transport Account", help="General transport account (transport added on vendor bills)")
