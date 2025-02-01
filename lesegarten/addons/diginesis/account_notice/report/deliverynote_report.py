# -*- coding: utf-8 -*-

from odoo import _, models, api
from odoo.exceptions import UserError
from odoo.tools.misc import formatLang, format_date
from odoo.tools.float_utils import float_round, float_is_zero, float_compare


class ReportDeliveryNote(models.AbstractModel):
    _name = 'report.account_notice.report_deliverynote'
    _description = 'Delivery Note Report'

    def _myformat_lang(self, value, digits=None, grouping=True, monetary=False, dp=False, currency_obj=False):
        return formatLang(self.env, value, digits=digits, grouping=grouping, monetary=monetary, dp=dp, currency_obj=currency_obj)

    def _myformat_date(self, value, lang_code=False, date_format=False):
        return format_date(self.env, value, lang_code=lang_code, date_format=date_format)

    @api.model
    def _get_report_values(self, docids, data):
        model = 'account.notice'
        docs = self.env[model].browse(docids)

        return {
            'doc_ids': docids,
            'doc_model': model,
            'docs': docs,
            'format_lang': self._myformat_lang,
            'format_date': self._myformat_date,
        }