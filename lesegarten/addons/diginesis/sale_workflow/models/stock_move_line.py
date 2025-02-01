# -*- coding: utf-8 -*-

from odoo import _, api, fields, tools, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero, float_round


class StockMoveLine(models.Model):
    _name = "stock.move.line"
    _inherit = "stock.move.line"

    notice_line_ids = fields.One2many('account.notice.line', 'stock_move_line_id',
                                         help="Technical field used only for browsing between notice and picking. Do not use to determine quantities.")

    def _prepare_notice_line(self):
        self.ensure_one()
        """
         Pentru fiecare linie de livrare (care se incandreaza (are cantiate>0) pentru avizat cf politicii de facturare)
        """
        account = self.location_id and self.location_id.property_account_income_location_id or self.product_id._get_product_accounts()['income']

        return {'product_id': self.product_id and self.product_id.id or False,
            'quantity': self._get_notice_line_qty(),
            'uom_id': self.product_uom_id and self.product_uom_id.id or False,
            'lot_id': self.lot_id and self.lot_id .id or False,
            'account_id': account and account.id or False,
            'stock_move_line_id': self.id,
            }

    def _post_prepare_notice_line_name(self, prepared_notice_line, name_parts):
        self.ensure_one()

        if not name_parts:
            return False

        template = self._get_notice_line_name_template()
        new_name_parts = name_parts.copy()

        #we'll just hardcode conditions here; maybe improve
        if not self.company_id.origin_in_notice_line_description:
            for key in ['picking_name', 'sale_name']:
                if new_name_parts.get(key):
                    new_name_parts[key] = ''

        res = []
        for key in sorted(template.keys()):
            if new_name_parts.get(template[key]):
                res.append(new_name_parts.get(template[key]))

        return ", ".join(filter(lambda x: x, res))

    def _get_notice_line_name_template(self):
        return {3: "notice_line_name", 0: "sale_name", 1: "picking_name", 2: "move_name"}

    def _hook_prepare_notice_line(self):
        return {}

    def _get_notice_line_qty(self):
        self.ensure_one()

        if not self.product_id:
            return 0

        if self.product_id.invoice_policy == 'delivery':
            if self.state == 'done':
                return self.qty_done
        else:
            return self.state == 'done' and self.qty_done or self.product_uom_qty

        return 0
