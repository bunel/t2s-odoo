# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from datetime import date, timedelta
from odoo import api, fields, models, tools, _
from odoo.tools import float_compare, date_utils


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = "account.move"

    approved_by_id = fields.Many2one('res.users', string='Approved by', readonly=True, tracking=True, states={'draft': [('readonly', False)]})
    last_exchange_rate = fields.Float(string='Exchange Rate', tracking=True, digits=(12, 12), help='Invoice exchange rate. When invoice currency is changed this field stores the rate used.')
    rate = fields.Float(string="Rate", tracking=True, digits=(12, 12), help='Invoice forced rate. Keep empty to use the currency from invoice date.',)
    amount_untaxed_signed_abs = fields.Monetary(string='Untaxed Amount Signed', store=True, readonly=True,
         compute='_compute_amount_abs', currency_field='company_currency_id', help="Untaxed Amount Signed without sign (always positive)")
    amount_tax_signed_abs = fields.Monetary(string='Tax Signed', store=True, readonly=True,
         compute='_compute_amount_abs', currency_field='company_currency_id', help="Tax Signed without sign (always positive)")
    amount_total_signed_abs = fields.Monetary(string='Total Signed', store=True, readonly=True,
         compute='_compute_amount_abs', currency_field='company_currency_id', help="Total Signed without sign (always positive)")
    amount_total_in_currency_signed_abs = fields.Monetary(string='Total in Currency Signed', store=True, readonly=True,
         compute='_compute_amount_abs', currency_field='currency_id', help="Total Signed without sign (always positive)")
    amount_residual_signed_abs = fields.Monetary(string='Amount Due Signed', store=True,
         compute='_compute_amount_abs', currency_field='company_currency_id', help="Amount Due Signed without sign (always positive)")

    @api.depends('amount_untaxed_signed', 'amount_tax_signed', 'amount_total_signed', 'amount_total_in_currency_signed', 'amount_residual_signed')
    def _compute_amount_abs(self):
        for move in self:
            move.amount_untaxed_signed_abs = abs(move.amount_untaxed_signed or 0)
            move.amount_tax_signed_abs = abs(move.amount_tax_signed or 0)
            move.amount_total_signed_abs = abs(move.amount_total_signed or 0)
            move.amount_total_in_currency_signed_abs = abs(move.amount_total_in_currency_signed or 0)
            move.amount_residual_signed_abs = abs(move.amount_residual_signed or 0)

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        if args is None:
            args = []
        if name and operator == "ilike":
            recs = self.search(['|', ("ref", operator, name), (self._rec_name or 'name', operator, name)] + args, limit=limit)
            if recs:
                return recs.name_get()
        return super().name_search(name=name, args=args, operator=operator, limit=limit)

    def _get_name_invoice_report(self):
        """ This method need to be inherit by the localizations if they want to print a custom invoice report instead of
        the default one. For example please review the l10n_ar module """
        self.ensure_one()
        return 'diginesis_invoice.report_invoice_document'

    @api.onchange('rate')
    def _onchange_rate(self):
        self.with_context(invoice_manually_rate=self.rate or 0,check_move_validity=False).line_ids._onchange_amount_currency()
        self._onchange_recompute_dynamic_lines()

    def action_post(self):
        for move in self.filtered(lambda x: x.company_currency_id and x.currency_id and x.company_currency_id.id != x.currency_id.id and not x.rate):
            move.write({'rate': move.currency_id.with_context(date=move.invoice_date or fields.Date.context_today(move)).inverse_rate})
        self.write({'approved_by_id': self.env.user.id})

        return super(AccountMove, self).action_post()

    def _get_accounting_date(self, invoice_date, has_tax):
        """We want to keep the accounting date as is set by user, for vendor bills
            We don't care about vendor bill name
        """
        lock_dates = self._get_violated_lock_dates(invoice_date, has_tax)
        today = fields.Date.today()
        highest_name = self.highest_name or self._get_last_sequence(relaxed=True)
        number_reset = self._deduce_sequence_number_reset(highest_name)
        if lock_dates:
            invoice_date = lock_dates[-1][0] + timedelta(days=1)
        if self.is_sale_document(include_receipts=True):
            if lock_dates:
                if not highest_name or number_reset == 'month':
                    return min(today, date_utils.get_month(invoice_date)[1])
                elif number_reset == 'year':
                    return min(today, date_utils.end_of(invoice_date, 'year'))

        return invoice_date


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.onchange('amount_currency')
    def _onchange_amount_currency(self):
        lines_with_rate = self.filtered(lambda x: x.move_id.rate)
        lines_wo_rate = self - lines_with_rate

        super(AccountMoveLine, lines_wo_rate)._onchange_amount_currency()

        for line in lines_with_rate:
            rate = line.move_id.rate
            company = line.move_id.company_id

            balance = company.currency_id.round(line.amount_currency * rate)

            line.debit = balance if balance > 0.0 else 0.0
            line.credit = -balance if balance < 0.0 else 0.0

            if not line.move_id.is_invoice(include_receipts=True):
                continue

            line.update(line._get_fields_onchange_balance())
            line.update(line._get_price_total_and_subtotal())

    @api.model
    def _get_fields_onchange_subtotal_model(self, price_subtotal, move_type, currency, company, date):
        """ We assume self.context('invoice_manually_rate') is always inverse_rate (The currency of rate 1 to the rate of the currency.)
        """

        if not self.env.context.get('invoice_manually_rate'):
            return super()._get_fields_onchange_subtotal_model(price_subtotal, move_type, currency, company, date)

        rate = self.env.context.get('invoice_manually_rate')
        if move_type in self.move_id.get_outbound_types():
            sign = 1
        elif move_type in self.move_id.get_inbound_types():
            sign = -1
        else:
            sign = 1

        amount_currency = price_subtotal * sign
        balance = company.currency_id.round(amount_currency * rate)

        return {
            'amount_currency': amount_currency,
            'currency_id': currency.id,
            'debit': balance > 0.0 and balance or 0.0,
            'credit': balance < 0.0 and -balance or 0.0,
        }
