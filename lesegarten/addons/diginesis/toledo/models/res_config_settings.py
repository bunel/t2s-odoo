# -*- coding: utf-8 -*-
from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
	_inherit = 'res.config.settings'
	
	invoice_drafter_partner_id = fields.Many2one('res.partner', related="company_id.invoice_drafter_partner_id",
												 readonly=False,)
	company_currency_pricelist = fields.Many2one('product.pricelist', related="company_id.company_currency_pricelist",
												 readonly=False, )