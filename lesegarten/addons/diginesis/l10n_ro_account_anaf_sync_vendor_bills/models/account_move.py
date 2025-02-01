# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from datetime import date, timedelta
from odoo import api, fields, models, tools, _
from odoo.tools import float_compare, date_utils


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = "account.move"

    spv_vendor_bill_ids = fields.One2many('spv.vendor.bill', 'invoice_id', string="Spv Bill Mapped")


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = "account.move.line"

    @api.onchange('product_id')
    def _onchange_product_id(self):

        lines_wo_vendor_bill = self.filtered(lambda x: not x.move_id or not x.move_id.spv_vendor_bill_ids)
        res = super(AccountMoveLine, lines_wo_vendor_bill)._onchange_product_id()
        if res is not None:
            return res
