# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, Warning
from odoo.tools import float_compare, float_round


class AccountMoveLine(models.Model):
	_inherit = "account.move.line"

	notice_line_id = fields.One2many('account.notice.line', 'invoice_line_id', string="Related Notice Line", help="Notice Line related to this account move line")
	accounted_notice_line_id = fields.Many2one('account.notice.line', string="Source Notice Line", help="Notice Line that generated this account move line")

