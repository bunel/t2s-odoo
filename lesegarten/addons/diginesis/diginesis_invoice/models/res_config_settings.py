# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
	_inherit = 'res.config.settings'
	
	add_invoice_allocate_difference_line = fields.Boolean(related="company_id.add_invoice_allocate_difference_line", readonly=False)
