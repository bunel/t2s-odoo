# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang, format_amount


class AccountNotice(models.Model):
    _inherit = 'account.notice'
    _name = 'account.notice'

    purchase_id = fields.Many2one('purchase.order', store=False, readonly=True,
                                  states={'draft': [('readonly', False)]},
                                  string='Purchase Order',
                                  help="Auto-complete from a past purchase order.")

    @api.onchange('purchase_id')
    def _onchange_purchase_auto_complete(self):
        """ Load from an old purchase order.
            This should be identical to PurchaseOrder.action_create_notice
        """

        if not self.purchase_id:
            return

        notice_vals = self.purchase_id.with_company(self.purchase_id.company_id)._prepare_notice()

        if not self._should_autocomplete_purchase(notice_vals):
            raise UserError(_("There is a mismatch between the selected purchase order and this notice. Please check Partner / Currency / Location of the selected purchase order."))

        # Copy data from PO
        self.update(notice_vals)

        pickings = self.env['stock.picking']

        # Copy purchase lines.
        po_lines = self.purchase_id.order_line
        new_lines = self.env['account.notice.line']
        for line in po_lines.filtered(lambda l: not l.display_type):
            new_line_vals = line._prepare_notice_line()
            if not new_line_vals:
                continue
            if self.location_id and self.location_id.valuation_out_account_id:
                new_line_vals['account_id'] = self.location_id.valuation_out_account_id.id

            new_line = new_lines.new(new_line_vals)
            new_lines += new_line

            pickings |= line.mapped('move_ids.picking_id').filtered(lambda x: x.state == 'assigned')

        if self.ids:
            pickings.write({'notice_id': self.ids[0]})

         # Compute notice_origin.
        origins = set(self.notice_line_ids.mapped('purchase_line_ids.order_id.name'))
        self.origin = ','.join(list(origins))

        self.purchase_id = False

    def _should_autocomplete_purchase(self, vals_from_purchase):
        self.ensure_one()

        if not vals_from_purchase:
            return True

        if self.partner_id:
            if vals_from_purchase.get('partner_id') and vals_from_purchase['partner_id'] != self.partner_id.id:
                return False

        if self.location_id:
            if vals_from_purchase.get('location_id') and vals_from_purchase['location_id'] != self.location_id.id:
                return False

        if self.currency_id:
            if vals_from_purchase.get('currency_id') and vals_from_purchase['currency_id'] != self.currency_id.id:
                return False

        return True

    def _get_purchases(self):
        return self.mapped('notice_line_ids.purchase_line_ids.order_id')

    def get_order_reference(self):
        self and self.ensure_one()

        if self.env.company.print_notice_custom_reference:
            purchase_names = list(set(filter(lambda x: x, [purchase.name for purchase in self._get_purchases()])))
            if purchase_names:
                return ','.join(purchase_names)

        return super().get_order_reference()


class AccountNoticeLine(models.Model):
    _inherit = 'account.notice.line'


    purchase_line_ids = fields.Many2many('purchase.order.line', 'purchase_line_notice_line_rel', 'notice_line_id', 'purchase_line_id', string='Purchase Lines', copy=False)

    def _prepare_account_move_line(self, move=False):
        self.ensure_one()
        aml_currency = move and move.currency_id or self.currency_id
        res = {
            'name': '%s: %s' % (self.notice_id.name, self.name),
            'product_id': self.product_id.id,
            'product_uom_id': self.uom_id.id,
            'quantity': self.quantity,
            'notice_line_id': [(4, self.id)],
            'account_id': self.notice_id.account_id and self.notice_id.account_id.id or False,
        }

        if aml_currency == self.currency_id:
            res.update({'price_unit': self.price_unit })

        if not move:
            return res

        if self.currency_id == move.company_id.currency_id:
            currency = False
        else:
            currency = move.currency_id

        res.update({
            'move_id': move.id,
            'currency_id': currency and currency.id or False,
            'date_maturity': move.invoice_date_due,
            'partner_id': move.partner_id.id,
        })
        return res



