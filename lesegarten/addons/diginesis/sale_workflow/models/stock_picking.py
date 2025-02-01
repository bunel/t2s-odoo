# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError
import ast
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, format_datetime
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.tools.misc import format_date

from odoo.addons.account_notice.models.stock_picking import NOTICE_TYPE_FROM_PICKING


class Picking(models.Model):
    _inherit = "stock.picking"

    invoice_id = fields.Many2one('account.move', 'Invoice', copy=False)
    outgoing_notice_id = fields.Many2one('account.notice', string="Notice", store=True, copy=False, compute="_compute_outgoing_notice")

    @api.depends('move_line_ids', 'move_line_ids.notice_line_ids')
    def _compute_outgoing_notice(self):
        for picking in self:
            picking.outgoing_notice_id = (picking.mapped('move_line_ids.notice_line_ids.notice_id').ids + [False])[0]

    def do_notice(self):
        """ will be split by picking / notice type """
        self.ensure_one()

        notice = self._do_outgoing_notice()

        action = self._get_action_view_notice(notices=notice)
        return action

    def _do_outgoing_notice(self):
        self.ensure_one()

        notice_vals = self._prepare_notice()
        sale = self.sale_id
        if sale:
            notice_vals.update(sale._prepare_notice())
            notice_vals['origin'] = "{0}, {1}".format(sale.name or '', notice_vals['origin'] or '')

        notice_vals.update(self._hook_prepare_notice())

        noticeable_lines = self._get_noticeable_lines()
        if not noticeable_lines:
            raise self._nothing_to_notice_error()

        notice_vals['notice_line_ids'] = [(0, 0, notice_line) for notice_line in self._prepare_notice_lines(sale, noticeable_lines)]

        return self.env['account.notice'].create(notice_vals)


    def _prepare_notice(self):
        self.ensure_one()

        company = self.company_id
        if not company.customer_notice_journal_id:
            raise UserError(_("Please configure Customer Notice Journal in Accounting Settings."))

        if not company.customer_notice_account_id:
            raise UserError(_("Please configure Customer Notice Account in Accounting Settings."))

        notice_vals = {
            'partner_id': (self.mapped('partner_id.commercial_partner_id').ids + [False])[0],
            'address_warehouse_id': (self.mapped('location_id.warehouse_id.partner_id').ids + [False])[0],
            'address_delivery_id': self.partner_id and self.partner_id.id or False,
            'date': fields.Datetime.now(),
            'currency_id': self.company_id.currency_id.id,
            'company_id': company.id,
            'journal_id': company.customer_notice_journal_id.id,
            'account_id': company.customer_notice_account_id.id,
            'location_id': self.location_id.id,
            'origin': self.name or '',
        }

        notice_vals.update(self._prepare_notice_type())
        return notice_vals

    def _hook_prepare_notice(self):
        return {}

    def _prepare_notice_lines(self, sale, noticeable_lines):
        self and self.ensure_one()
        if not noticeable_lines:
            return []

        res = []
        for move_line in noticeable_lines:
            notice_line_vals = self._prepare_notice_line(sale, move_line)
            if notice_line_vals:
                res.append(notice_line_vals)

        return res

    def _prepare_notice_line(self, sale, noticeable_line):
        move_id = noticeable_line.move_id
        sale_line_id = move_id and move_id.sale_line_id or False

        notice_line_vals = noticeable_line._prepare_notice_line()

        line_values_to_update = {'name': noticeable_line._post_prepare_notice_line_name(
                                            notice_line_vals,
                                            {
                                                'sale_name': sale.name or '',
                                                'picking_name': self.name or '',
                                                'move_name': move_id and move_id.name or '',
                                                'notice_line_name': notice_line_vals.get('name') or False
                                            }
                                        )
                                }

        notice_line_vals.update(line_values_to_update)
        notice_line_vals.update({'price_unit': sale_line_id and sale_line_id.price_unit or 0,
                                 'discount': sale_line_id and sale_line_id.discount or '',
                                 'sale_line_ids': [(6, 0, sale_line_id.ids)] if sale_line_id else False,
                                 })
        notice_line_vals.update(noticeable_line._hook_prepare_notice_line())
        return notice_line_vals


    def _prepare_notice_type(self):
        self.ensure_one()

        return {'type': self._get_notice_type()}

    @api.model
    def _nothing_to_notice_error(self):
        return UserError(_(
            "There is nothing to notice!\n\n"
            "Reason(s) of this behavior could be:\n"
            "- You should deliver your products before noticing them.\n"
            "- You should modify the invoicing policy of your product: Open the product, go to the "
            "\"Sales\" tab and modify invoicing policy from \"delivered quantities\" to \"ordered "
            "quantities\"."
        ))

    def _get_noticeable_lines(self):
        """Return the noticeable lines for order `self`."""
        noticeable_lines = self.env['stock.move.line']

        for move_line in self.mapped('move_line_ids'):
            line_qty = move_line._get_notice_line_qty()
            if line_qty:
                noticeable_lines |= move_line

        return noticeable_lines

    def _get_notice_type(self):
        self.ensure_one()

        key = "{0}|{1}".format(self.location_usage, self.location_dest_usage)

        if NOTICE_TYPE_FROM_PICKING.get(key):
            return NOTICE_TYPE_FROM_PICKING[key]

        return 'internal'


    def action_view_notice(self):
        return self._get_action_view_notice(self.notice_id | self.outgoing_notice_id)

    def _get_action_view_notice(self, notices):
        self.ensure_one()

        map = {'out_notice': "account_notice.action_notice_customer_tree",
                'out_refund': "account_notice.action_notice_customer_tree",
                'in_notice': "account_notice.action_notice_supplier_tree",
                'in_refund': "account_notice.action_notice_supplier_tree",
                'internal': "account_notice.action_notice_internal_tree",
                }

        notice_type = self._get_notice_type()
        xml_id = map.get(notice_type) or "account_notice.action_notice_customer_tree"

        action = self.env["ir.actions.actions"]._for_xml_id(xml_id)

        if notices and len(notices) > 1:
            action['domain'] = [('id', 'in', notices.ids)]
        elif notices:
            form_view = [(self.env.ref('account_notice.account_notice_customer_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = notices.id
        else:
            action['domain'] = [('id', '=', False)]
        return action

