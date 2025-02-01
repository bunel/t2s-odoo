# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import UserError


class AccountMoveReversal(models.TransientModel):
    _name = 'account.move.reversal'
    _inherit = 'account.move.reversal'

    refund_method = fields.Selection(default='refund')
