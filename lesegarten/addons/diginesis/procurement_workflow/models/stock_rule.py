# -*- coding: utf-8 -*-
from datetime import datetime
from odoo.tools import float_compare
from odoo import api, fields, models, SUPERUSER_ID, _


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _prepare_purchase_order(self, company_id, origins, values):
        res = super(StockRule, self)._prepare_purchase_order(company_id, origins, values)
        if res.get('partner_id'):
            partner = self.env['res.partner'].browse(res['partner_id'])
            res.update({'reception_mode': partner.reception_mode, 'incoterm_id': partner.supplier_incoterm_id and partner.supplier_incoterm_id.id or False})

        return res
