from odoo import api, fields, models, tools, _
from datetime import datetime
from odoo.exceptions import ValidationError, UserError


class Company(models.Model):
	_name = 'res.company'
	_inherit = 'res.company'
	
	goods_transit_account_id = fields.Many2one('account.account', string="Account for Goods in Transit", help="Account for Goods in Transit")
	merge_receptions_by_invoice = fields.Boolean(string="Merge Receptions", default=False)