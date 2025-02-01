# -*- coding: utf-8 -*-
import time
from odoo import api, fields, models
from odoo.tools.misc import formatLang, format_date


class ReportPartnerBankStatement(models.AbstractModel):
    _name = 'report.diginesis_invoice.report_partnerbankstatement'
    _description = 'Partner statement report'

    #move_type
    INVOICE_MOVE_TYPE_MAP = {"customer": ['out_invoice', 'out_refund'],
                             'vendor': ['in_invoice', 'in_refund'],
                             'vendor_customer': ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']}

    # def _get_account_move_lines(self, partner_ids):
    #     date = self.env.context.get('date', fields.Date.today())
    #     invoice_type = self.env.context.get('invoice_type')
    #
    #     where = ["m.state='posted'"]
    #     params = []
    #     if invoice_type and self.INVOICE_MOVE_TYPE_MAP.get(invoice_type):
    #         where.append("m.move_type in %s")
    #         params.append(tuple(self.INVOICE_MOVE_TYPE_MAP.get(invoice_type)))
    #
    #     self.env.cr.execute("""WITH invoice_data AS
    #         (SELECT at.type,
    #                 (CASE WHEN m.move_type IN ('in_invoice', 'in_refund') THEN m.ref ELSE '' END) || ' ' || m.name AS move_name,
    #                 l.date,
    #                 l.name,
    #                 l.ref,
    #                 l.date_maturity,
    #                 l.partner_id,
    #                 l.blocked,
    #         CASE WHEN at.type = 'receivable'
    #             THEN SUM(l.debit) - SUM(l.credit)
    #             ELSE SUM(l.credit) - SUM(l.debit)
    #         END AS value,
    #         CASE WHEN l.date_maturity <= %s
    #         THEN
    #         CASE WHEN at.type = 'receivable' and sum(l.debit)<>0
    #             THEN SUM(l.debit) - SUM(l.credit) - COALESCE(SUM(prc.p_rec),0) - COALESCE(SUM(prf.p_rec),0)
    #             ELSE
    #                 CASE WHEN at.type = 'receivable' and sum(l.credit)<>0
    #                     THEN SUM(l.debit) - SUM(l.credit) + COALESCE(SUM(prc.p_rec),0) + COALESCE(SUM(prf.p_rec),0)
    #                     ELSE
    #                         CASE WHEN at.type = 'payable' and sum(l.debit)<>0
    #                             THEN SUM(l.credit) - SUM(l.debit) + COALESCE(SUM(prc.p_rec),0) + COALESCE(SUM(prf.p_rec),0)
    #                             ELSE
    #                                 CASE WHEN at.type = 'payable' and sum(l.credit)<>0
    #                                 THEN SUM(l.credit) - SUM(l.debit) - COALESCE(SUM(prc.p_rec),0) - COALESCE(SUM(prf.p_rec),0)
    #                                 END
    #                     END
    #             END
    #         END
    #     ELSE 0
    #     END AS mat,
    #     CASE WHEN at.type = 'receivable' and sum(l.debit)<>0
    #         THEN SUM(l.debit) - SUM(l.credit) - COALESCE(SUM(prc.p_rec),0) - COALESCE(SUM(prf.p_rec),0)
    #         ELSE
    #             CASE WHEN at.type = 'receivable' and sum(l.credit)<>0
    #                 THEN SUM(l.debit) - SUM(l.credit) + COALESCE(SUM(prc.p_rec),0) + COALESCE(SUM(prf.p_rec),0)
    #                 ELSE
    #                     CASE WHEN at.type = 'payable' and sum(l.debit)<>0
    #                         THEN SUM(l.credit) - SUM(l.debit) + COALESCE(SUM(prc.p_rec),0) + COALESCE(SUM(prf.p_rec),0)
    #                         ELSE
    #                             CASE WHEN at.type = 'payable' and sum(l.credit)<>0
    #                                 THEN SUM(l.credit) - SUM(l.debit) - COALESCE(SUM(prc.p_rec),0) - COALESCE(SUM(prf.p_rec),0)
    #                             END
    #                     END
    #             END
    #     END AS sold
    #
    #     FROM account_move_line l
    #     JOIN account_account on account_account.id=l.account_id
    #     JOIN account_account_type at ON at.id=account_account.user_type_id
    #     JOIN account_move m ON m.id=l.move_id
    #     LEFT JOIN
    #             (SELECT apr.debit_move_id, sum(apr.amount) AS p_rec from account_partial_reconcile apr
    #                 JOIN account_move_line aml1 ON aml1.id=apr.credit_move_id AND aml1.date<=%s
    #                 WHERE aml1.partner_id IN %s
    #                 GROUP BY apr.debit_move_id
    #             ) AS prc
    #         ON l.id=prc.debit_move_id
    #     LEFT JOIN
    #             (SELECT apr.credit_move_id, sum(apr.amount) AS p_rec from account_partial_reconcile apr
    #                 JOIN account_move_line aml1 ON aml1.id=apr.debit_move_id AND aml1.date<=%s
    #                 WHERE aml1.partner_id IN %s
    #                 GROUP BY apr.credit_move_id
    #         ) AS prf
    #         ON l.id=prf.credit_move_id
    #
    #     WHERE l.partner_id IN %s AND at.type IN ('receivable', 'payable') AND l.date <= %s AND {0}
    #     GROUP BY l.date, l.name, l.ref, l.date_maturity, l.partner_id, at.type, l.blocked, l.move_id, m.name, m.move_type, m.ref, l.account_id
    #     ORDER BY at.type, l.date
    #     )
    #     SELECT * FROM invoice_data WHERE ROUND(ABS(sold),2) > 0
    #     """.format(" AND ".join(where)), (date, date, tuple(partner_ids), date, tuple(partner_ids), tuple(partner_ids), date) + tuple(params))
    #
    #     query_res = self.env.cr.dictfetchall()
    #
    #     res = dict((partner_id, []) for partner_id in partner_ids)
    #     for row in query_res:
    #         res[row.pop('partner_id')].append(row)
    #     return res

    def _compute(self, data):
        if any([not data.get(k) for k in ['date', 'account_ids', 'currency_id', 'partner_ids']]):
            return {}

        invoice_type = self.env.context.get('invoice_type')

        where = ["am.state='posted'"]
        params = []
        if invoice_type and self.INVOICE_MOVE_TYPE_MAP.get(invoice_type):
            where.append("am.move_type in %s")
            params.append(tuple(self.INVOICE_MOVE_TYPE_MAP.get(invoice_type)))

        reconcile_query = []
        if not data.get('include_reconciled', False):
            reconcile_query.append("HAVING round(abs(aml.balance)-coalesce(sum(apr.amount),0)::numeric,2)<>0")

        self.env.cr.execute("""
            SELECT report.aml_date as date,
                CASE WHEN aj.type in ('bank', 'cash') THEN report.aml_name
                    WHEN aj.type in ('sale', 'general') THEN am.name
                            ELSE report.aml_ref END as move_name,
                        CASE WHEN aj.type in ('bank', 'cash', 'sale') THEN report.aml_ref
                            WHEN aj.type in ('general') THEN report.aml_name ||' '|| report.aml_ref
                            ELSE am.name END as ref,
                        '/' as name,
                        report.aml_blocked as blocked,
                    report.aml_date_maturity as date_maturity,
                    account_account_type.type as type,
                    report.partner_id as partner_id,
                    report.value * (CASE WHEN functionality.code='pasive' THEN -1 ELSE 1 END) as value,
                    report.balance * (CASE WHEN functionality.code='pasive' THEN -1 ELSE 1 END) as sold,
                    CASE WHEN report.aml_date_maturity <= %s THEN report.balance * (CASE WHEN functionality.code='pasive' THEN -1 ELSE 1 END) ELSE 0 END as mat        
                FROM
                    ( SELECT
                        aml.id,
                        aml.move_id,
                        aml.journal_id,
                        aml.account_id,
                        aml.partner_id,
                        aml.name as aml_name,
                        aml.ref as aml_ref,
                        aml.date as aml_date,
                        aml.date_maturity as aml_date_maturity,
                        aml.blocked as aml_blocked,
                        aml.balance as value,                    
                        round(abs(aml.balance)-coalesce(sum(apr.amount),0)::numeric,2) * (CASE WHEN aml.balance < 0 THEN -1 ELSE 1    END) as balance 

                        FROM account_move_line aml
                        LEFT JOIN account_partial_reconcile apr ON
                            (aml.id=apr.credit_move_id or aml.id=apr.debit_move_id) AND
                            apr.max_date<=%s
                        WHERE aml.id IN 
                            (SELECT id FROM account_move_line 
                                    WHERE partner_id in %s
                                    AND account_id in %s
                                    AND (currency_id is null OR currency_id=%s)
                                    AND date<=%s) 
                        GROUP BY aml.id, aml.move_id, aml.journal_id, aml.partner_id, aml.account_id, aml.balance, aml.name, aml.ref, aml.date, aml.date_maturity, aml.blocked
                        {0}
                    ) report
                JOIN account_account aa ON aa.id=report.account_id            
                JOIN account_journal aj on aj.id=report.journal_id
                JOIN account_move am on am.id=report.move_id
                LEFT JOIN account_account_functionality functionality on aa.functionality_id=functionality.id
                LEFT JOIN account_account_type ON account_account_type.id=aa.user_type_id
                WHERE {1}
                ORDER BY report.aml_date_maturity, report.partner_id 
            """.format(" ".join(reconcile_query), " AND ".join(where)), (
            data['date'], data['date'], tuple(data['partner_ids']), tuple(data['account_ids']), data['currency_id'],
            data['date']) + tuple(params))

        res = self.env.cr.dictfetchall()

        return res

    def _compute_currency(self, data):

        if any([not data.get(k) for k in ['date', 'account_ids', 'currency_id', 'partner_ids']]):
            return {}

        invoice_type = self.env.context.get('invoice_type')

        where = ["am.state='posted'"]
        params = []
        if invoice_type and self.INVOICE_MOVE_TYPE_MAP.get(invoice_type):
            where.append("am.move_type in %s")
            params.append(tuple(self.INVOICE_MOVE_TYPE_MAP.get(invoice_type)))

        reconcile_query = []
        if not data.get('include_reconciled', False):
            # Verify company currency balance to exclude move lines reconciled in mix currency operation.
            reconcile_query.append("HAVING round(abs(aml.balance)-coalesce(sum(apr.amount),0)::numeric,2)<>0")

        self.env.cr.execute("""
                SELECT report.aml_date as date,
                        CASE WHEN aj.type in ('bank', 'cash') THEN report.aml_name
                            WHEN aj.type in ('sale', 'general') THEN am.name
                            ELSE report.aml_ref END as move_name,
                        CASE WHEN aj.type in ('bank', 'cash', 'sale') THEN report.aml_ref
                            WHEN aj.type in ('general') THEN report.aml_name ||' '|| report.aml_ref
                            ELSE am.name END as ref,
                        '/' as name,
                        report.aml_blocked as blocked,
                    report.aml_date_maturity as date_maturity,
                    account_account_type.type as type,
                    report.partner_id as partner_id,
                    report.value * (CASE WHEN functionality.code='pasive' THEN -1 ELSE 1 END) as value,
                    report.balance * (CASE WHEN functionality.code='pasive' THEN -1 ELSE 1 END) as sold,
                    CASE WHEN report.aml_date_maturity <= %s THEN report.balance * (CASE WHEN functionality.code='pasive' THEN -1 ELSE 1 END) ELSE 0 END as mat                    
                FROM
                    (SELECT 
                        aml.id,
                        aml.move_id,
                        aml.journal_id,
                        aml.account_id,                
                        aml.partner_id,                
                        aml.name as aml_name,                
                        aml.ref as aml_ref,                
                        aml.date as aml_date,        
                        aml.date_maturity as aml_date_maturity,        
                        aml.blocked as aml_blocked,                     
                        aml.amount_currency as value,  
                        CASE WHEN aml.id=apr.credit_move_id 
                                THEN round(abs(aml.amount_currency)-coalesce(sum(apr.credit_amount_currency),0)::numeric,2) * (CASE WHEN aml.amount_currency < 0 THEN -1 ELSE 1 END)
                            WHEN aml.id=apr.debit_move_id
                                THEN round(abs(aml.amount_currency)-coalesce(sum(apr.debit_amount_currency),0)::numeric,2) * (CASE WHEN aml.amount_currency < 0 THEN -1 ELSE 1 END)
                            ELSE 
                                round(abs(aml.amount_currency)::numeric,2) * (CASE WHEN aml.amount_currency < 0 THEN -1 ELSE 1 END)
                        END as balance

                        FROM account_move_line aml
                        LEFT JOIN account_partial_reconcile apr ON
                            (aml.id=apr.credit_move_id or aml.id=apr.debit_move_id) AND
                            apr.max_date<=%s

                        WHERE aml.id IN 
                            (SELECT id FROM account_move_line 
                                    WHERE partner_id IN %s
                                    AND account_id IN %s
                                    AND currency_id=%s
                                    AND date<=%s) 
                        GROUP BY aml.id, aml.move_id, aml.account_id, aml.journal_id, aml.partner_id, aml.name, aml.ref, 
                                aml.date, aml.date_maturity, aml.blocked, aml.amount_currency, apr.credit_move_id, apr.debit_move_id, apr.credit_amount_currency, apr.debit_amount_currency 
                        {0}
                    ) report
                JOIN account_account aa ON aa.id=report.account_id            
                JOIN account_journal aj on aj.id=report.journal_id
                JOIN account_move am on am.id=report.move_id
                LEFT JOIN account_account_functionality functionality on aa.functionality_id=functionality.id
                LEFT JOIN account_account_type ON account_account_type.id=aa.user_type_id
                WHERE {1}
                ORDER BY report.aml_date_maturity, report.partner_id   
            """.format(" ".join(reconcile_query), " AND ".join(where)), (
            data['date'], data['date'], tuple(data['partner_ids']), tuple(data['account_ids']), data['currency_id'],
            data['date']) + tuple(params))

        res = self.env.cr.dictfetchall()
        return res

    def _get_account_move_lines(self, partner_ids, data):
        compute_method = '_compute'
        company_currency = self.env.user.company_id.currency_id
        if data.get('currency_id') and company_currency and data['currency_id'] != company_currency.id:
            compute_method = '_compute_currency'

        res = {}
        for partner_id in partner_ids:
            partner_data = data.copy()
            partner_data['partner_ids'] = [partner_id]
            res[partner_id] = getattr(self, compute_method)(partner_data)

        return res

    def _myformat_lang(self, value, digits=None, grouping=True, monetary=False, dp=False, currency_obj=False):
        return formatLang(self.env, value, digits=digits, grouping=grouping, monetary=monetary, dp=dp, currency_obj=currency_obj)

    def _myformat_date(self, value, lang_code=False, date_format=False):
        return format_date(self.env, value, lang_code=lang_code, date_format=date_format)

    def _prepare_lines(self, partner_ids, move_lines):
        lines_to_display = {}
        totals = {}
        for partner_id in partner_ids:
            lines_to_display[partner_id] = {}
            totals[partner_id] = {}
            for line_tmp in move_lines[partner_id]:
                line = line_tmp.copy()
                acc_type = line['type']

                lines_to_display[partner_id].setdefault(acc_type, [])
                totals[partner_id].setdefault(acc_type, dict((fn, 0.0) for fn in ['sold', 'mat']))

                lines_to_display[partner_id][acc_type].append(line)
                if not line['blocked']:
                    totals[partner_id][acc_type]['sold'] += line['sold'] or 0
                    totals[partner_id][acc_type]['mat'] += line['mat'] or 0

        return lines_to_display, totals

    def _get_report_values(self, docids, data=None):

        form_data = data.get('form')

        date = form_data.get('date') or fields.Date.today()
        invoice_type = form_data.get('invoice_type') or 'vendor_customer'
        docids = form_data.get('partner_ids') or []
        docmodel = 'res.partner'
        docs = self.env[docmodel].browse(docids) if docids else self.env[docmodel]

        lines = self.with_context(date=date, invoice_type=invoice_type)._get_account_move_lines(docids, form_data)
        #company_currency = self.env.user.company_id.currency_id

        lines_to_display, totals = self._prepare_lines(docids, lines)

        company_currency = self.env.user.company_id.currency_id
        currency_id = company_currency
        if form_data.get('currency_id') and company_currency and form_data['currency_id'] != company_currency.id:
            currency_id = self.env['res.currency'].browse(form_data['currency_id'])

        return {
            'doc_ids': docids,
            'doc_model': docmodel,
            'docs': docs,
            'Lines': lines_to_display,
            'Totals': totals,
            'Date': date,
            'formatLang': self._myformat_lang,
            'format_date': self._myformat_date,
            'my_company': self.env.user.company_id,
            'currency_id': currency_id,
        }
