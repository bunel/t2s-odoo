# -*- coding: utf-8 -*-
from odoo import _, _lt, api, fields, models
from odoo.exceptions import UserError


class Warehouse(models.Model):
    _name = "stock.warehouse"
    _inherit = "stock.warehouse"

    nir_number_sequence_id = fields.Many2one('ir.sequence', string='NIR Number Sequence')