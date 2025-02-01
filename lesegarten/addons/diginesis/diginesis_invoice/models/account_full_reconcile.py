# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class AccountFullReconcile(models.Model):
    _inherit = "account.full.reconcile"

    reconciled_lines_date = fields.Date('Reconciled Lines Date', compute="_get_reconciled_lines_date", store=True,
                                        help="Most recent (biggest) reconciliation date among all reconciled move lines")

    @api.depends('reconciled_line_ids', 'reconciled_line_ids.date')
    def _get_reconciled_lines_date(self):
        for full_rec in self:
            full_rec.reconciled_lines_date = full_rec.reconciled_line_ids and max(
                full_rec.mapped('reconciled_line_ids.date')) or False
