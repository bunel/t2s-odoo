# -*- coding: utf-8 -*-
import math
import re
import time
from datetime import datetime, timedelta

from odoo import api, fields, models, tools, _

class Currency(models.Model):
    _inherit = "res.currency"

    reference_currency_id = fields.Many2one('res.currency', 'Reference Currency', index=True)
    similar_currency_id = fields.Many2one('res.currency', string="Similar Currency")
    rate_difference = fields.Float('Difference (%)', help="Percentage difference from reference currency.")

    def _get_rates(self, company, date):

        previous_date = (date or fields.Date.today()) - timedelta(days=1)
        return super()._get_rates(company, previous_date)

    def _convert(self, from_amount, to_currency, company, date, round=True):
        """Returns the converted amount of ``from_amount``` from the currency
           ``self`` to the currency ``to_currency`` for the given ``date`` and
           company.

           Conversion will not be performed if reference currency is the same for self and to_currency

           :param company: The company from which we retrieve the convertion rate
           :param date: The nearest date from which we retriev the conversion rate.
           :param round: Round the result or not
        """
        self, to_currency = self or to_currency, to_currency or self
        assert self, "convert amount from unknown currency"
        assert to_currency, "convert amount to unknown currency"
        assert company, "convert amount from unknown company"
        assert date, "convert amount from unknown date"
        # apply conversion rate

        if self.similar_currency_id and to_currency.similar_currency_id and self.similar_currency_id.id == to_currency.similar_currency_id.id:
            to_amount = from_amount
            return to_currency.round(to_amount) if round else to_amount

        return super()._convert(from_amount, to_currency, company, date, round=round)


class CurrencyRate(models.Model):
    _inherit = "res.currency.rate"

    def write(self, vals):
        res = super().write(vals)
        self._update_referencing()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res._update_referencing()
        return res

    def _update_referencing(self):
        ResCurrency = self.env['res.currency']

        for rate in self.filtered(lambda x: x.currency_id):
            currency_id = rate.currency_id

            referencing_currencies = ResCurrency.search([('reference_currency_id', '=', currency_id.id)])
            if referencing_currencies:
                current_rate = rate.inverse_company_rate
                current_rate_name = rate.name

                for referencing_currency in referencing_currencies:
                    new_inverse_rate = current_rate + current_rate * referencing_currency.rate_difference / 100
                    if new_inverse_rate > 0:
                        new_rate = 1 / new_inverse_rate

                        self.env.cr.execute("""SELECT id FROM res_currency_rate WHERE currency_id=%s AND name=%s """, (referencing_currency.id, current_rate_name))
                        res_ref_rate = self.env.cr.fetchone()
                        if res_ref_rate and res_ref_rate[0]:
                            self.env.cr.execute("""UPDATE res_currency_rate SET rate=%s WHERE id=%s """, (new_rate, res_ref_rate[0]))
                        else:
                            self.create([{'name': current_rate_name, 'rate': new_rate, 'currency_id': referencing_currency.id}])
