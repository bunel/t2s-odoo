# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _, SUPERUSER_ID
from odoo.exceptions import ValidationError, RedirectWarning, UserError


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = "sale.order"

    payment_mode_id = fields.Many2one('account.payment.mode', string="Payment Mode")

    @api.onchange('partner_id')
    def _onchange_payment_mode_partner_id(self):
        if not self.payment_mode_id:
            self.payment_mode_id = (self.mapped('partner_id.payment_mode_id').ids + self.mapped('partner_id.commercial_partner_id.payment_mode_id').ids + [False])[0]

    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()
        res = super()._prepare_invoice()

        res.update({'payment_mode_id': self.payment_mode_id and self.payment_mode_id.id or False})
        return res