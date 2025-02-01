# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.tools import float_is_zero, float_compare
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_price_unit_for_svl_price_update(self):
        self.ensure_one()

        res = super(StockMove, self)._get_price_unit_for_svl_price_update()
        res = res or 0

        lc_valuation_lines = self.env['l10n.ro.stock.valuation.adjustment.lines'].search([('move_id', '=', self.id), ('cost_id.state', '=', 'done')])
        for lc_vl in lc_valuation_lines:
            res += lc_vl.price_unit_additional or 0

        return res
