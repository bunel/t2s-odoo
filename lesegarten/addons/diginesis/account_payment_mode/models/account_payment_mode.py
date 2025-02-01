# -*- coding: utf-8 -*-
from odoo import api, fields, models

class AccountPaymentMode(models.Model):
    _name = 'account.payment.mode'
    _description = "Account Payment Mode"

    name = fields.Char(string='Name', required=True, index=True)
    note = fields.Text(string='Description')

