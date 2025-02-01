# -*- coding: utf-8 -*-
from datetime import timedelta, datetime, date
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError, RedirectWarning

class ResCompany(models.Model):
	_inherit = "res.company"
	
	fancourier_slip_journal_id = fields.Many2one('account.journal', string="FanCourier Slip Journal")