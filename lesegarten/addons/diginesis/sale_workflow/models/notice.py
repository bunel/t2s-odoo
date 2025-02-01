# -*- coding: utf-8 -*-
from datetime import datetime, time
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang, format_amount


class AccountNotice(models.Model):
    _name = 'account.notice'
    _inherit = 'account.notice'

    delegate_id = fields.Many2one('res.partner', string="Delegate", readonly=True,
                       states={'draft': [('readonly', False)]})
    responsible_id = fields.Many2one('res.partner', string="Issued by", default=lambda self: self.env.user.partner_id)
    incoterm_id = fields.Many2one('account.incoterms', string="Incoterm", readonly=True,
                                  states={'draft': [('readonly', False)]})
    vehicle_reference = fields.Char(string="Vehicle Reference", readonly=True, states={'draft': [('readonly', False)]})
    autocomplete_picking_id = fields.Many2one('stock.picking', store=False, readonly=True,
                                  states={'draft': [('readonly', False)]},
                                  string='Autocomplete Picking',
                                  help="Auto-complete from a delivery / internal move.")
    sale_count = fields.Integer(string="Sales Count", compute='_count_sales')

    def _compute_pickings(self):
        res = super(AccountNotice, self)._compute_pickings()

        StockPicking = self.env['stock.picking']
        for notice in self:
            notice.picking_ids |= StockPicking.search([('outgoing_notice_id', '=', notice.id)])

    @api.onchange('autocomplete_picking_id')
    def onchange_autocomplete_picking_id(self):
        if not self.autocomplete_picking_id:
            return False

        notice_vals = self.autocomplete_picking_id._prepare_notice()

        if not self._should_autocomplete_picking(notice_vals):
            raise UserError(_("There is a mismatch between the selected picking and this notice. Please check Partner / Location of the selected picking."))

        picking = self.autocomplete_picking_id
        sale = picking.sale_id
        if sale:
            notice_vals.update(sale._prepare_notice())
            notice_vals['origin'] = "{0}, {1}".format(sale.name or '', notice_vals['origin'] or '')

        noticeable_lines = picking._get_noticeable_lines()
        if not noticeable_lines:
            raise picking._nothing_to_notice_error()

        notice_line_ids = []
        for move_line in noticeable_lines:
            move_id = move_line.move_id
            sale_line_id = move_id and move_id.sale_line_id or False

            notice_line_vals = move_line._prepare_notice_line()
            notice_line_vals.update({'name': "{0}, {1}, {2}{3}{4}".format(self.autocomplete_sale_id.name or '',
                                                                    picking.name or '',
                                                                    move_id and move_id.name or '',
                                                                    notice_line_vals.get('name') and ', ' or '',
                                                                    notice_line_vals.get('name') or ''),
                                     'price_unit': sale_line_id and sale_line_id.price_unit or 0,
                                     'discount': sale_line_id and sale_line_id.discount or '',
                                     'sale_line_ids': [(6, 0, sale_line_id.ids)] if sale_line_id else False,
                                     })
            notice_line_ids.append((0, 0, notice_line_vals))

        notice_vals['notice_line_ids'] = notice_line_ids
        self.update(notice_vals)

        self.autocomplete_picking_id = False

    def _should_autocomplete_picking(self, vals_from_picking):
        self.ensure_one()

        if not vals_from_picking:
            return True

        if self.partner_id:
            if vals_from_picking.get('partner_id') and vals_from_picking['partner_id'] != self.partner_id.id:
                return False

        if self.address_delivery_id:
            if vals_from_picking.get('address_delivery_id') and vals_from_picking['address_delivery_id'] != self.address_delivery_id.id:
                return False

        if self.location_id:
            if vals_from_picking.get('location_id') and vals_from_picking['location_id'] != self.location_id.id:
                return False

        if self.currency_id:
            if vals_from_picking.get('currency_id') and vals_from_picking['currency_id'] != self.currency_id.id:
                return False

        return True

    def _count_sales(self):
        for notice in self:
            notice.sale_count = len(notice._get_sales())

    def _get_sales(self):
        return self.mapped('notice_line_ids.sale_line_ids.order_id')

    def action_view_sales(self):
        return self._get_action_view_sale(self._get_sales())

    def _get_action_view_sale(self, sales):
        self.ensure_one()

        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_sale_order_form_view")

        if len(sales) > 1:
            action['domain'] = [('id', 'in', sales.ids)]
        elif sales:
            form_view = [(self.env.ref('sale.view_order_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = sales.id
        else:
            action['domain'] = [('id', '=', False)]
        return action

    def get_order_reference(self):
        self and self.ensure_one()

        if self.env.company.print_notice_custom_reference:
            sale_names = list(set(filter(lambda x: x, [sale.name for sale in self._get_sales()])))
            if sale_names:
                return ','.join(sale_names)

        return super().get_order_reference()


class AccountNoticeLine(models.Model):
    _name = 'account.notice.line'
    _inherit = 'account.notice.line'

    sale_line_ids = fields.Many2many('sale.order.line', 'sale_line_notice_line_rel', 'notice_line_id', 'sale_line_id', string='Sale Lines', copy=False)
    stock_move_line_id = fields.Many2one('stock.move.line', string="Stock Move Line", copy=False,
                                         help="Technical field used only for browsing between notice and picking. Do not use to determine quantities.")
