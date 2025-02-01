# -*- coding: utf-8 -*-
from odoo import api, fields, models, Command, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError

class AccountMove(models.Model):
    _name = "account.move"
    _inherit = "account.move"

    delegate_id = fields.Many2one('res.partner', string="Delegate")
    stockables_margin = fields.Monetary(string="Stockables Margin", currency_field="currency_id", compute="_compute_stockables_margin", store=True, copy=False)

    def _get_name_invoice_report(self):
        """ This method need to be inherit by the localizations if they want to print a custom invoice report instead of
        the default one. For example please review the l10n_ar module """
        self.ensure_one()
        return 'toledo.report_invoice_document'

    @api.depends('line_ids.price_subtotal', 'currency_id')
    def _compute_stockables_margin(self):
        def _get_stockables_amount(invoice):
            pickings = self.env['stock.picking'].search([('invoice_id', '=', invoice.id), ('state', '=', 'done')])
            repair_operations = invoice.mapped('repair_ids.operations')

            svls = pickings.mapped('move_line_ids.stock_valuation_layer_ids').filtered(lambda x: x.value and x.value < 0)
            svls |= repair_operations.mapped('move_id.stock_valuation_layer_ids')

            return sum([abs(svl.value) for svl in svls if svl.value])

        def _get_invoiced_amount(invoice):
            return sum([line.price_subtotal for line in record.invoice_line_ids if line.product_id and line.product_id.type == 'product'])

        company_currency = self.env.company.currency_id
        for record in self:
            stockables_amount = _get_stockables_amount(record)
            if record.move_type != 'out_invoice' or not record.currency_id or record.currency_id.id != company_currency.id or not stockables_amount:
                record.stockables_margin = 0
            else:
                record.stockables_margin = _get_invoiced_amount(record) - stockables_amount

