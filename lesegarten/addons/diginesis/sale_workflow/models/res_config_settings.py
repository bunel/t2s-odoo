# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    picking_in_invoice_line_description = fields.Boolean(related='company_id.picking_in_invoice_line_description', readonly=False, string='Picking in Invoice Line')
    special_rounding_currency_id = fields.Many2one(related="company_id.special_rounding_currency_id", readonly=False, string="Special currency for rounding")
    origin_in_notice_line_description = fields.Boolean(related='company_id.origin_in_notice_line_description', readonly=False,)
