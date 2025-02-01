# -*- coding: utf-8 -*-

from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools.misc import formatLang, format_date
from odoo.tools.float_utils import float_round, float_is_zero, float_compare


class ReportStockPickingIncoming(models.AbstractModel):
    _inherit = 'report.l10n_ro_stock_report.report_pickingincoming'

    def _get_landed_cost_lines(self, picking):
        SVAL = self.env['l10n.ro.stock.valuation.adjustment.lines']
        sval = self.env['l10n.ro.stock.valuation.adjustment.lines']
        if picking:
            move_ids = picking.mapped('move_lines').ids
            if move_ids:
                sval = SVAL.search([('move_id', 'in', move_ids), ('cost_id.state', '=', 'done')])

        return sval

    def _get_report_values(self, docids, data):
        res = super(ReportStockPickingIncoming, self)._get_report_values(docids, data)

        res.update({'get_landed_cost_lines': self._get_landed_cost_lines})
        return res
