# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = "account.move"

    payment_mode_id = fields.Many2one('account.payment.mode', string='Payment Mode')

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        res = super()._onchange_partner_id()

        if not self.payment_mode_id:
            self.payment_mode_id = (self.mapped('partner_id.payment_mode_id').ids + self.mapped('partner_id.commercial_partner_id.payment_mode_id').ids + [False])[0]

        return res