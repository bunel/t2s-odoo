# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class ResConfigSettings(models.TransientModel):
	_inherit = 'res.config.settings'

	fancourier_slip_journal_id = fields.Many2one("account.journal", related="company_id.fancourier_slip_journal_id", string="FanCourier Slip Journal", readonly=False)