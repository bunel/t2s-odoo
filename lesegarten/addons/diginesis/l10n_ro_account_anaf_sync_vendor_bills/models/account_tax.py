# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.tools.float_utils import float_round as round
from odoo.exceptions import UserError, ValidationError


class AccountTax(models.Model):
    _name = 'account.tax'
    _inherit = 'account.tax'

    is_for_spv_bills = fields.Boolean(string="Default for SPV Bill")
