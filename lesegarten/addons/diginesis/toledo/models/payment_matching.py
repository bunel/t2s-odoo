# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountReconciliation(models.AbstractModel):
    _name = 'account.reconciliation.widget'
    _inherit = 'account.reconciliation.widget'

    @api.model
    def _get_statement_line(self, st_line):
        """ Returns the data required by the bank statement reconciliation widget to display a statement line """

        res = super()._get_statement_line(st_line)
        res.update({'payment_ref': st_line.payment_ref})
        return res
