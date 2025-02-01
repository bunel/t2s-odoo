# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.modules.module import get_module_resource


class ResCompany(models.Model):
    _inherit = "res.company"

    picking_in_invoice_line_description = fields.Boolean(string='Picking in Invoice Line', default=True)
    special_rounding_currency_id = fields.Many2one('res.currency', string="for_rounding_currency_id")
    origin_in_notice_line_description = fields.Boolean(string='Origin in Notice Line', default=False)
