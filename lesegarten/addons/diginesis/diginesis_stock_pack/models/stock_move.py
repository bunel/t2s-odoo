# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero, float_round


class StockMove(models.Model):
    _name = "stock.move"
    _inherit = "stock.move"

    stock_tracking_id = fields.Many2one('stock.tracking', string="Stock Tracking")

    @api.model
    def _prepare_merge_moves_distinct_fields(self):
        distinct_fields = super(StockMove, self)._prepare_merge_moves_distinct_fields()
        distinct_fields += ['stock_tracking_id']
        return distinct_fields
