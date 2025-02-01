# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tools import float_compare, float_round, float_is_zero, OrderedSet


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _prepare_procurement_origin(self):
        self.ensure_one()
        if self.repair_id:
            return self.origin or self.repair_id.name
        return super()._prepare_procurement_origin()
