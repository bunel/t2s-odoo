# -*- coding: utf-8 -*-

from datetime import datetime, time
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang, format_amount
from odoo.addons.procurement_workflow.models.res_partner import RECEPTION_MODE


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    reception_mode = fields.Selection(RECEPTION_MODE, string="Reception Mode")
    notice_count = fields.Integer(compute="_compute_notice", compute_sudo=True, string='Notice Count')
    notice_ids = fields.Many2many('account.notice', compute="_compute_notice", compute_sudo=True, string='Notices', copy=False, store=True)

    @api.onchange('partner_id', 'company_id')
    def onchange_partner_id(self):
        res = super(PurchaseOrder, self).onchange_partner_id()
        if self.partner_id:
            self.reception_mode = self.partner_id.reception_mode
            self.incoterm_id = self.partner_id.supplier_incoterm_id
        else:
            self.reception_mode = False
            self.incoterm_id = False

        return res

    def _compute_notice(self):
        for order in self:
            notices = order.mapped('order_line.notice_line_ids.notice_id')
            order.notice_count = len(notices)
            order.notice_ids = notices

    def action_create_notice(self):
        """Create the notice associated to the PO. """
        notices = self.env['account.notice']

        for order in self:
            reception_mode = order.reception_mode
            if not reception_mode:
                continue

            method = "_create_workflow_notice_{0}".format(reception_mode)
            if hasattr(order, method):
                notices |= getattr(order, method)()

        return self.action_view_notice(notices)

    def _create_workflow_notice_notice_reception(self):

        AccountNotice = self.env['account.notice']
        StockLocation = self.env['stock.location']
        notices = self.env['account.notice']

        orders_with_unreceived_notices = self.mapped('notice_ids').filtered(lambda x: x.state not in ['receive', 'invoice'])
        if orders_with_unreceived_notices:
            raise UserError(_('PO already has a notice not yet received. Please first receive the existing notice.'))

        for order in self:
            notice_vals = order.with_company(self.company_id)._prepare_notice()
            notice_vals.update({'origin': order.name or '',
                               'notice_line_ids': []})

            pickings = self.env['stock.picking']

            # Copy purchase lines.
            po_lines = order.order_line
            for line in po_lines.filtered(lambda l: not l.display_type):
                new_line_vals = line._prepare_notice_line()
                if not new_line_vals:
                    continue
                if notice_vals.get('location_id'):
                    notice_location = StockLocation.browse(notice_vals['location_id'])
                    if notice_location and notice_location.valuation_out_account_id:
                        new_line_vals['account_id'] = notice_location.valuation_out_account_id.id
                notice_vals['notice_line_ids'].append((0, 0, new_line_vals))
                pickings |= line.mapped('move_ids.picking_id').filtered(lambda x: x.state == 'assigned')

            if not notice_vals['notice_line_ids']:
                raise UserError(_("There are not notice lines."))

            notice = AccountNotice.create(notice_vals)
            notices |= notice
            pickings.write({'notice_id': notice.id})

        return notices

    def _create_workflow_notice_bill_notice_reception(self):
        AccountNotice = self.env['account.notice']
        StockLocation = self.env['stock.location']
        notices = self.env['account.notice']

        for order in self:
            notice_vals = order.with_company(self.company_id)._prepare_notice()
            notice_vals.update({'origin': order.name or '',
                                'notice_line_ids': []})

            pickings = self.env['stock.picking']

            # Copy purchase lines.
            po_lines = order.order_line
            for line in po_lines.filtered(lambda l: not l.display_type):
                new_line_vals = line._prepare_notice_line()
                if not new_line_vals:
                    continue
                if notice_vals.get('location_id'):
                    notice_location = StockLocation.browse(notice_vals['location_id'])
                    if notice_location and notice_location.valuation_out_account_id:
                        new_line_vals['account_id'] = notice_location.valuation_out_account_id.id
                notice_vals['notice_line_ids'].append((0, 0, new_line_vals))
                pickings |= line.mapped('move_ids.picking_id').filtered(lambda x: x.state == 'assigned')

            if not notice_vals['notice_line_ids']:
                raise UserError(_("There are not notice lines."))

            notice = AccountNotice.create(notice_vals)
            notices |= notice
            pickings.write({'notice_id': notice.id})

        return notices

    def action_view_notice(self, notices=None):
        action = self.env.ref('account_notice.action_notice_supplier_tree')
        result = action.read()[0]

        notices = notices or self.notice_ids
        notice_count = len(notices)

        if notice_count > 1:
            result['domain'] = [('id', 'in', notices.ids)]
        elif notice_count == 1:
            res = self.env.ref('account_notice.account_notice_supplier_form')
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = notices.id
        else:
            result = {'type': 'ir.actions.act_window_close'}

        return result

    def _prepare_notice(self):
        """Prepare the dict of values to create the new notice for a purchase order.
        """
        self.ensure_one()

        reception_mode = self.reception_mode
        if not reception_mode:
            return {}

        method = "_prepare_notice_{0}".format(reception_mode)
        if hasattr(self, method):
            return getattr(self, method)()

        return {}

    def _prepare_notice_notice_reception(self):
        company = self.env.company
        journal = company.vendor_notice_journal_id
        if not journal:
            raise UserError(_('Please define an vendor notice journal for the company %s (%s).') % (self.company_id.name, self.company_id.id))

        location = self.picking_type_id and self.picking_type_id.default_location_dest_id or False
        warehouse = self.picking_type_id and self.picking_type_id.warehouse_id or False

        notice_vals = {
            'company_id': self.company_id.id,
            'journal_id': journal.id,
            'account_id': company.vendor_notice_account_id and company.vendor_notice_account_id.id or False,
            'location_id': location and location.id or False,
            'type': 'in_notice',
            'currency_id': self.currency_id and self.currency_id.id or False,
            'partner_id': self.partner_id and self.partner_id.id or False,
            'address_delivery_id': warehouse and warehouse.partner_id and warehouse.partner_id.id or False,
        }
        return notice_vals

    def _prepare_notice_bill_notice_reception(self):
        company = self.env.company
        journal = company.vendor_notice_journal_id
        if not journal:
            raise UserError(_('Please define an vendor notice journal for the company %s (%s).') % (self.company_id.name, self.company_id.id))

        account = company.goods_transit_account_id
        if not account:
            raise UserError(_('Please configure Goods in Transit account.'))

        location = self.picking_type_id and self.picking_type_id.default_location_dest_id or False
        warehouse = self.picking_type_id and self.picking_type_id.warehouse_id or False

        notice_vals = {
            'company_id': self.company_id.id,
            'journal_id': journal.id,
            'account_id': account and account.id or False,
            'location_id': location and location.id or False,
            'type': 'in_notice',
            'currency_id': self.currency_id and self.currency_id.id or False,
            'partner_id': self.partner_id and self.partner_id.id or False,
            'address_delivery_id': warehouse and warehouse.partner_id and warehouse.partner_id.id or False,
        }
        return notice_vals

    def action_create_workflow_invoice(self):
        """Create the invoice associated to the PO. """

        moves = self.env['account.move']

        for order in self:
            reception_mode = order.reception_mode
            if not reception_mode:
                continue

            method = "_create_workflow_invoice_{0}".format(reception_mode)
            if hasattr(order, method):
                moves |= getattr(order, method)()

        return self.action_view_invoice(moves)
        
    def _create_workflow_invoice_notice_reception(self):

        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        # 1) Prepare invoice vals and clean-up the section lines
        invoice_vals_list = []
        for order in self:
            if order.invoice_status != 'to invoice':
                continue

            order = order.with_company(order.company_id)
            pending_section = None
            # Invoice values.
            invoice_vals = order._prepare_invoice()
            # Invoice line values (keep only necessary sections).
            for line in order.order_line:
                if line.display_type == 'line_section':
                    pending_section = line
                    continue
                if not line.product_id or line.product_id.detailed_type == 'service':
                    if not float_is_zero(line.qty_to_invoice, precision_digits=precision):
                        if pending_section:
                            invoice_vals['invoice_line_ids'].append(
                                (0, 0, pending_section._prepare_account_move_line()))
                            pending_section = None
                        invoice_vals['invoice_line_ids'].append((0, 0, line._prepare_account_move_line()))

                else:
                    invoice_lines_values_from_po = line._prepare_account_move_line()
                    notice_lines = line._get_notice_lines()
                    for notice_line in notice_lines.filtered(lambda x: not x.invoice_line_id or x.notice_id.state not in ['receive', 'invoice']):
                        if not float_is_zero(notice_line.quantity, precision_digits=precision):
                            invoice_line_values = invoice_lines_values_from_po
                            invoice_line_values.update(notice_line._prepare_account_move_line())

                            invoice_vals['invoice_line_ids'].append((0, 0, invoice_line_values))

            if not invoice_vals['invoice_line_ids']:
                raise UserError(_('There is no invoiceable line.'))

            invoice_vals_list.append(invoice_vals)

        # 2) Create invoices.
        moves = self.env['account.move']
        AccountMove = self.env['account.move'].with_context(default_move_type='in_invoice')
        for vals in invoice_vals_list:
            moves |= AccountMove.with_company(vals['company_id']).create(vals)

        # 4) Some moves might actually be refunds: convert them if the total amount is negative
        # We do this after the moves have been created since we need taxes, etc. to know if the total
        # is actually negative or not
        moves.filtered(
            lambda m: m.currency_id.round(m.amount_total) < 0).action_switch_invoice_into_refund_credit_note()

        # 5) Update receptions connected to processed notices - moved to account_move_line create()
        return moves

    def _create_workflow_invoice_bill_reception(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        # 1) Prepare invoice vals and clean-up the section lines
        invoice_vals_list = []
        for order in self:
            if order.invoice_status != 'to invoice':
                continue

            order = order.with_company(order.company_id)
            pending_section = None
            # Invoice values.
            invoice_vals = order._prepare_invoice()
            # Invoice line values (keep only necessary sections).
            for line in order.order_line:
                if line.display_type == 'line_section':
                    pending_section = line
                    continue
                if not float_is_zero(line.qty_to_invoice, precision_digits=precision):
                    if pending_section:
                        invoice_vals['invoice_line_ids'].append((0, 0, pending_section._prepare_account_move_line()))
                        pending_section = None
                    invoice_vals['invoice_line_ids'].append((0, 0, line._prepare_account_move_line()))
            if not invoice_vals['invoice_line_ids']:
                raise UserError(_('There is no invoiceable line.'))
            invoice_vals_list.append(invoice_vals)

        # 2) Create invoices.
        moves = self.env['account.move']
        AccountMove = self.env['account.move'].with_context(default_move_type='in_invoice')
        for vals in invoice_vals_list:
            moves |= AccountMove.with_company(vals['company_id']).create(vals)

        # 3) Some moves might actually be refunds: convert them if the total amount is negative
        # We do this after the moves have been created since we need taxes, etc. to know if the total
        # is actually negative or not
        moves.filtered(
            lambda m: m.currency_id.round(m.amount_total) < 0).action_switch_invoice_into_refund_credit_note()

        # 4) Update receptions connected to processed po lines - moved to account_move_line create()

        return moves

    def _create_workflow_invoice_bill_notice_reception(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        goods_transit_account = self.env.company.goods_transit_account_id
        if not goods_transit_account:
            raise UserError(_('Please configure Goods in Transit account.'))

        invoice_vals_list = []
        for order in self:
            if order.invoice_status != 'to invoice':
                continue

            order = order.with_company(order.company_id)
            pending_section = None
            # Invoice values.
            invoice_vals = order._prepare_invoice()
            # Invoice line values (keep only necessary sections).
            for line in order.order_line:
                if line.display_type == 'line_section':
                    pending_section = line
                    continue
                if not float_is_zero(line.qty_to_invoice, precision_digits=precision):
                    if pending_section:
                        line_vals = pending_section._prepare_account_move_line()
                        if pending_section.product_id and pending_section.product_id.detailed_type in ['consu', 'product']:
                            line_vals.update({'account_id': goods_transit_account.id})
                        invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                        pending_section = None
                    line_vals = line._prepare_account_move_line()
                    if line.product_id and line.product_id.detailed_type in ['consu', 'product']:
                        line_vals.update({'account_id': goods_transit_account.id})
                    invoice_vals['invoice_line_ids'].append((0, 0, line_vals))

            if not invoice_vals['invoice_line_ids']:
                raise UserError(_('There is no invoiceable line.'))

            invoice_vals_list.append(invoice_vals)

        # 2) Create invoices.
        moves = self.env['account.move']
        AccountMove = self.env['account.move'].with_context(default_move_type='in_invoice')
        for vals in invoice_vals_list:
            moves |= AccountMove.with_company(vals['company_id']).create(vals)

        # 3) Some moves might actually be refunds: convert them if the total amount is negative
        # We do this after the moves have been created since we need taxes, etc. to know if the total
        # is actually negative or not
        moves.filtered(
            lambda m: m.currency_id.round(m.amount_total) < 0).action_switch_invoice_into_refund_credit_note()

        # 4) Update receptions connected to processed po lines - moved to account_move_line create()
        return moves


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    qty_noticed = fields.Float(compute='_compute_qty_noticed', string="Noticed Qty", digits='Product Unit of Measure', store=True, copy=False)
    notice_line_ids = fields.Many2many('account.notice.line', 'purchase_line_notice_line_rel', 'purchase_line_id', 'notice_line_id', string='Notice Lines', copy=False)

    @api.depends('notice_line_ids.notice_id.state', 'notice_line_ids.quantity', 'product_uom_qty',
                 'order_id.state')
    def _compute_qty_noticed(self):
        for line in self:
            qty = 0.0
            for note_line in line._get_notice_lines():
                if note_line.notice_id.state not in ['cancel']:
                    if note_line.notice_id.type == 'in_notice':
                        qty += note_line.uom_id._compute_quantity(note_line.quantity, line.product_uom)
                    elif note_line.notice_id.type == 'in_refund':
                        qty -= note_line.uom_id._compute_quantity(note_line.quantity, line.product_uom)
            line.qty_noticed = qty

    def _get_notice_lines(self):
        self.ensure_one()
        return self.notice_line_ids

    def _prepare_notice_line(self):
        self.ensure_one()

        reception_mode = self.order_id.reception_mode
        if not reception_mode:
            return {}

        method = "_prepare_notice_line_{0}".format(reception_mode)
        if hasattr(self, method):
            return getattr(self, method)()

        return {}

    def _prepare_notice_line_notice_reception(self):
        if self.product_id.detailed_type == 'service':
            return {}

        ready_pickings = self.move_ids.filtered(lambda x: x.state == 'assigned').mapped('picking_id.name')
        if not ready_pickings:
            return {}

        quantity = (self.product_qty or 0) - (self.qty_noticed or 0)
        if float_compare(quantity, 0, precision_rounding=self.product_uom.rounding) <= 0:
            return {}

        accounts_data = self.product_id.product_tmpl_id.get_product_accounts()
        account = accounts_data['stock_input']

        name = '{0}: {1} {2}'.format(self.order_id.name, ','.join(ready_pickings), self.name)

        res = {
            'name': name,
            'product_id': self.product_id.id,
            'uom_id': self.product_uom.id,
            'quantity': quantity,
            'price_unit': self.price_unit,
            'account_id': account and account.id or False,
            'purchase_line_ids': [(4, self.id)],
        }

        return res

    def _prepare_notice_line_bill_notice_reception(self):
        if self.product_id.detailed_type == 'service':
            return {}

        ready_pickings = self.move_ids.filtered(lambda x: x.state == 'assigned').mapped('picking_id.name')
        if not ready_pickings:
            return {}

        quantity = (self.qty_invoiced or 0) - (self.qty_noticed or 0)
        if float_compare(quantity, 0, precision_rounding=self.product_uom.rounding) <= 0:
            return {}

        invoice_lines = self._get_invoice_lines()
        invoice_lines = invoice_lines.filtered(lambda x: not x.notice_line_id)
        if not invoice_lines:
            return {}

        accounts_data = self.product_id.product_tmpl_id.get_product_accounts()
        account = accounts_data['stock_input']

        name = '{0}: {1} {2} {3}'.format(self.order_id.name, ','.join(list(set(invoice_lines.mapped('move_id.name')))), ','.join(ready_pickings), self.name)

        res = {
            'name': name,
            'product_id': self.product_id.id,
            'uom_id': self.product_uom.id,
            'quantity': quantity,
            'price_unit': self.price_unit,
            'account_id': account and account.id or False,
            'purchase_line_ids': [(4, self.id)],
            'invoice_line_id': invoice_lines[0].id,
        }

        return res

    def _compute_qty_invoiced(self):
        """ We ignore Control Policy in Bill Reception workflow"""
        res = super(PurchaseOrderLine, self)._compute_qty_invoiced()

        for line in self.filtered(lambda x: x.order_id.reception_mode in ['bill_reception', 'bill_notice_reception']):
            # compute qty_to_invoice
            if line.order_id.state in ['purchase', 'done']:
                line.qty_to_invoice = line.product_qty - line.qty_invoiced
            else:
                line.qty_to_invoice = 0

        return res

    def _prepare_account_move_line(self, move=False):
        self.ensure_one()

        res = super(PurchaseOrderLine, self)._prepare_account_move_line(move=move)

        if self.product_id and self.product_id.detailed_type != 'service':
            location_account_id = self.mapped('order_id.picking_type_id.default_location_dest_id.valuation_out_account_id')
            if location_account_id:
                res.update({'account_id': location_account_id.id})
        return res
