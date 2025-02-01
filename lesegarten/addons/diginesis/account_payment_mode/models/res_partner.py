# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    payment_mode_id = fields.Many2one('account.payment.mode', string='Payment Mode')