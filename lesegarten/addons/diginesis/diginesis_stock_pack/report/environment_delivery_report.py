# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools import float_is_zero, float_compare, float_round


class EnvironmentDeliveryReport(models.AbstractModel):
    _name = 'environment.delivery.report'
    _description = 'Environment Delivery Report'
    _inherit = 'account.report'

    filter_date = {'mode': 'range', 'filter': 'this_month'}
    filter_multi_company = None
    filter_account_accounts = None
    filter_account_type = None
    filter_with_pack = [
        {'id': 'all', 'name': _('All'), 'selected': False},
        {'id': 'yes', 'name': _('With Pack'), 'selected': False},
        {'id': 'no', 'name': _('No Pack'), 'selected': False},
    ]

    @api.model
    def _get_options_with_pack(self, options):
        with_packs = 'all'
        for with_pack_option in options.get('with_pack', []):
            if with_pack_option['selected']:
                with_packs = with_pack_option['id']
        return with_packs

    def _get_templates(self):
        templates = super(EnvironmentDeliveryReport, self)._get_templates()
        templates['search_template'] = 'diginesis_stock_pack.search_template'
        return templates

    def _get_columns_name(self, options):
        columns = [
            {'name': ''},
            {'name': _('Partner')},
            {'name': _('Doc. Number')},
            {'name': _('Doc. Date')},
            {'name': _('Pack Date')},
            {'name': _('Gross Weight'), 'class': 'number'},
            {'name': _('Net Weight'), 'class': 'number'},
            {'name': _('Packaging Weight'), 'class': 'number'},
            {'name': _('Paper+Cardboard Weight'), 'class': 'number'},
            {'name': _('Foil Weight'), 'class': 'number'},
            {'name': _('Wood Weight'), 'class': 'number'},
            {'name': _('Pallets'), 'class': 'number'},
            {'name': _('Pallets Weight'), 'class': 'number'},
        ]

        return columns

    @api.model
    def _create_environment_delivery_report_line(self, options, vals):
        prec_digits = 1
        columns = [{'name': c} for c in [
            vals['partner_name'], vals['document_number'], vals['document_date'],
            vals['tracking_date'],
            vals['gross_weight'], vals['net_weight'], vals['packaging_weight'],
            round(vals['paper_cardboard_weight'], prec_digits), vals['foil_weight'], vals['wood_weight'],
            vals['pallet_count'], vals['pallet_weight']
        ]]

        option_with_pack = self._get_options_with_pack(options)
        if option_with_pack != 'all':
            if (option_with_pack == 'yes' and not vals.get('has_pack')) or (option_with_pack == 'no' and vals.get('has_pack')):
                return {}

        return {
            'id': vals['id'],
            'caret_options': 'stock.move',
            'model': 'stock.move',
            'name': vals['document_number'],
            'columns': columns,
            'level': 2,
            'class':  '' if vals.get('has_pack') else 'color-red',
        }

    @api.model
    def _decode_options(self, options):
        return options['date']['date_from'], options['date']['date_to']

    @api.model
    def _prepare_query(self, date_from, date_to):
        query = """
    SELECT * 
    FROM (
        SELECT
            row_number() over () AS id,
            min(res_partner.name) AS partner_name, 
            COALESCE(stock_picking.name, '') || ' - ' ||min(COALESCE(a.notice_name, account_move.name, '')) AS document_number, 
            min(COALESCE(date(stock_picking.date), a.notice_date, account_move.invoice_date)) AS document_date, 
            min(stock_tracking.date) AS tracking_date, 
            min(COALESCE(stock_tracking.gross_weight, 0)) AS gross_weight,
            min(COALESCE(stock_tracking.net_weight, 0)) AS net_weight,
            min(COALESCE(stock_tracking.gross_weight, 0)) - min(COALESCE(stock_tracking.net_weight, 0)) AS packaging_weight,
            min(COALESCE(stock_tracking.gross_weight, 0)) - min(COALESCE(stock_tracking.net_weight, 0)) - (min(COALESCE(stock_tracking.product_pallet_count, 0)) * %(foil_coefficient)s ) - (min(COALESCE(stock_tracking.product_pallet_count, 0)) * min(COALESCE(product_pallet.weight, 0))) AS paper_cardboard_weight,
            min(COALESCE(stock_tracking.product_pallet_count, 0)) * %(foil_coefficient)s AS foil_weight,
            min(COALESCE(stock_tracking.product_pallet_count, 0)) * min(COALESCE(product_pallet.weight, 0)) AS wood_weight,
            min(COALESCE(stock_tracking.product_pallet_count, 0)) AS pallet_count,
            min(COALESCE(product_pallet.weight, 0)) AS pallet_weight,
            CASE WHEN stock_tracking.id IS NULL THEN 0 ELSE 1 END as has_pack
        FROM
            stock_move    
            JOIN stock_location ON stock_location.id = stock_move.location_dest_id
            JOIN stock_move_line ON stock_move_line.move_id=stock_move.id
                        
            LEFT JOIN stock_tracking ON stock_tracking.id=stock_move.stock_tracking_id
            LEFT JOIN product_pack ON product_pack.id = stock_tracking.product_pack_id
            LEFT JOIN stock_picking ON stock_picking.id=stock_move.picking_id
            LEFT JOIN product_pallet ON product_pallet.id = stock_tracking.product_pallet_id
            LEFT JOIN account_move ON account_move.id = stock_picking.invoice_id            
            LEFT JOIN LATERAL  
                (SELECT account_notice.name as notice_name, account_notice.date as notice_date
                    FROM account_notice 
                    JOIN account_notice_line ON account_notice_line.notice_id=account_notice.id 
                    WHERE account_notice_line.stock_move_line_id=stock_move_line.id
                        AND account_notice.state<>'draft'
                    GROUP BY account_notice.name, account_notice.date
                ) a ON True   
            LEFT JOIN res_partner ON res_partner.id=stock_picking.partner_id        
            LEFT JOIN res_country ON res_country.id = res_partner.country_id         
        WHERE
            stock_move.state='done' AND stock_location.usage='customer'
            AND stock_picking.date BETWEEN %(date_start)s AND %(date_end)s
            AND (res_partner.country_id IS NULL OR (res_partner.country_id <> %(company_country)s AND res_country.l10n_ro_is_ue='t'))
        GROUP BY stock_move.id, stock_picking.name, res_partner.name, stock_tracking.id
    ) as b
    ORDER BY b.document_date
        """

        company = self.env.company
        params = {
            'foil_coefficient': self.env.company.stock_packaging_foil_coefficient or 0.2,
            'date_start': date_from,
            'date_end': date_to,
            'company_country': company.country_id and company.country_id.id or 0,
        }

        return query, params

    @api.model
    def _fill_missing_values(self, vals_list):
        return vals_list

    @api.model
    def _get_lines(self, options, line_id=None):
        self.env['stock.tracking'].check_access_rights('read')

        date_from, date_to = self._decode_options(options)

        query, params = self._prepare_query(date_from, date_to)

        self._cr.execute(query, params)
        query_res = self._cr.dictfetchall()

        # Create lines
        lines = []
        for vals in self._fill_missing_values(query_res):
            line = self._create_environment_delivery_report_line(options, vals)
            if line:
                lines.append(line)

        return lines

    @api.model
    def _get_report_name(self):
        return _('Environment Delivery Report')

