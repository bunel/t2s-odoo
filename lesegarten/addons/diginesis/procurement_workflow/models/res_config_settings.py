# -*- coding: utf-8 -*-
from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
	_inherit = 'res.config.settings'

	goods_transit_account_id = fields.Many2one('account.account', related="company_id.goods_transit_account_id", readonly=False,  help="Account for Goods in Transit")
	merge_receptions_by_invoice = fields.Boolean(related="company_id.merge_receptions_by_invoice", readonly=False, help="Merge receptions based on invoice")
