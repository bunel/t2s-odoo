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
    _description = "Account Notice"
    _inherit = ['mail.thread']
    _order = "date DESC"

    @api.depends('notice_line_ids.price_subtotal', 'currency_id')
    def _compute_amount(self):
        for notice in self:
            total = sum(line.price_subtotal for line in notice.notice_line_ids)
            notice.amount_total = notice.currency_id.round(total) if notice.currency_id else total

    print_with_values = fields.Boolean(string="Quantitive Value Notice", default=True)

    name = fields.Char(string='Notice Number', index=True,
                       readonly=True, states={'draft': [('readonly', False)]}, copy=False)
    origin = fields.Char(string='Source Document',
                         help="Reference of the document that produced this invoice.",
                         readonly=True, states={'draft': [('readonly', False)]})
    type = fields.Selection([
        ('out_notice', 'Customer Notice'),
        ('out_refund', 'Customer Refund Notice'),
        ('in_notice', 'Vendor Notice'),
        ('in_refund', 'Vendor Refund Notice'),
        ('internal', 'Internal Notice'),
    ], readonly=True, index=True, change_default=True, tracking=True, states={'draft': [('readonly', False)]})
    reference = fields.Char(string='Reference',
                            help="The partner reference.", readonly=True,
                            states={'draft': [('readonly', False)]})
    comment = fields.Text('Additional Information', readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('receive', 'Received'),
        ('deliver', 'Delivered'),
        ('invoice', 'Invoiced'),
        ('cancel', 'Cancelled'),
    ], string='Status', index=True, readonly=True, default='draft',
        tracking=True, copy=False)
    date = fields.Date(string='Date', copy=False, help="Keep empty to use the current date.", readonly=True,
                       states={'draft': [('readonly', False)]})
    partner_id = fields.Many2one('res.partner', string='Partner', change_default=True, required=True, readonly=True,
                                 states={'draft': [('readonly', False)]}, tracking=True)
    address_warehouse_id = fields.Many2one('res.partner', string="Company WorkPoint Address", readonly=True,
                                           states={'draft': [('readonly', False)]})
    address_delivery_id = fields.Many2one('res.partner', string="Delivery Address", readonly=True,
                                          states={'draft': [('readonly', False)]})
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, readonly=True,
                                 states={'draft': [('readonly', False)]})
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position', readonly=True,
                                     states={'draft': [('readonly', False)]})
    account_id = fields.Many2one('account.account', string='Account', readonly=True,
                             states={'draft': [('readonly', False)]},
                             domain=[('deprecated', '=', False)],
                             help="The partner account.")
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=True,
                                  states={'draft': [('readonly', False)]},
                                  tracking=True)
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string="Company Currency",
                                          readonly=True)
    company_id = fields.Many2one('res.company', string='Company', change_default=True, required=True, readonly=True,
                                 states={'draft': [('readonly', False)]},
                                 default=lambda s: s.env.company.id)
    rate = fields.Float('Rate', digits=(12, 4), readonly=True, states={'draft': [('readonly', False)]})
    account_move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True, index=True, ondelete='restrict',
                              copy=False, help="Link to the automatically generated Journal Items.")
    move_name = fields.Char(string='Journal Entry Name', readonly=False, default=False, copy=False,
                            help="Technical field holding the number given to the notice, automatically set when the notice is validated then stored to set the same number again if the notice is cancelled, set to draft and re-validated.")
    location_id = fields.Many2one('stock.location', string="Location")
    notice_line_ids = fields.One2many('account.notice.line', 'notice_id', string='Notice Lines',
                                            readonly=True, states={'draft': [('readonly', False)]}, copy=True)
    picking_ids = fields.Many2many('stock.picking', string="Pickings", copy=False, compute="_compute_pickings")
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_compute_amount')

    def name_get(self):
        res = []
        for notice in self:
            res.append((notice.id, '%s' % (notice.name or _('Draft'))))
        return res

    def get_order_reference(self):
        self and self.ensure_one()

        return self.origin

    def _compute_pickings(self):
        StockPicking = self.env['stock.picking']
        for notice in self:
            notice.picking_ids = StockPicking.search([('notice_id', '=', notice.id)])

    def unlink(self):
        if self.filtered(lambda x: x.state not in ['draft']):
            raise UserError(_('Only Draft Notice(s) can be deleted.'))

        return super(AccountNotice, self).unlink()

    def action_confirm(self):
        for notice in self:
            if notice.move_name:
                name = notice.move_name
            else:
                name = notice.journal_id.secure_sequence_id.next_by_id()
            vals = {'state': 'confirm', 'name': name, 'move_name': name}
            notice_date = notice.date
            if not notice.date:
                notice_date = fields.Date.today()
                vals.update({'date': notice_date})
            if notice.currency_id and notice.currency_id.id != notice.company_currency_id.id:
                if not notice.rate:
                    vals.update({'rate': notice.currency_id.with_context(date=notice_date).inverse_rate})

            notice.write(vals)

        self.action_move_create()

        return True

    def action_cancel(self):
        account_moves = self.mapped('account_move_id').with_context(force_delete=True)
        account_moves.mapped('line_ids').remove_move_reconcile()
        account_moves.button_draft()

        self.write({'state': 'cancel', 'account_move_id': False})
        account_moves.unlink()

        return True

    def action_cancel_draft(self):
        self.filtered(lambda x: x.state == 'cancel').write({'state': 'draft'})
        return True

    def action_receive(self):
        self.write({'state': 'receive'})
        return True

    def action_invoice(self):
        self.write({'state': 'invoice'})
        return True

    def action_move_create(self):

        vendor_notices = self.filtered(lambda x: x.type in ['in_notice', 'in_refund'])
        vendor_notices.action_vendor_move_create()

        customer_notices = self.filtered(lambda x: x.type in ['out_notice', 'out_refund'])
        customer_notices.action_customer_move_create()

    def action_vendor_move_create(self):

        AccountMove = self.env['account.move']
        Partner = self.env['res.partner']

        for notice in self:
            diff_currency = notice.currency_id and notice.currency_id.id != notice.company_currency_id.id and True or False
            notice_account = notice.account_id
            currency = notice.currency_id
            date = notice.date

            imls = notice.notice_line_move_line_get()

            total, total_currency, imls = notice.compute_notice_totals(imls)

            counterpart_iml = []
            for move_line in imls:
                counterpart_iml.append({
                        'type': 'dest',
                        'name': move_line.get('name'),
                        'price': (-1 if total < 0 else 1) * abs(move_line.get('price')),
                        'account_id': notice_account.id,
                        'date_maturity': date,
                        'amount_currency': diff_currency and move_line.get('amount_currency') or 0,
                        'currency_id': diff_currency and currency and currency.id or False,
                        'accounted_notice_line_id': move_line.get('accounted_notice_line_id'),
                    })
            imls += counterpart_iml

            move_partner = Partner._find_accounting_partner(notice.partner_id)
            move_lines = [(0, 0, self.line_get_convert(l, move_partner.id)) for l in imls]
            move_lines = notice.finalize_note_move_lines(move_lines)

            move_vals = {
                'ref': notice.reference,
                'line_ids': move_lines,
                'journal_id': notice.journal_id.id,
                'date': notice.date,
                'narration': notice.comment,
                'name': notice.name,
            }

            move = AccountMove.create(move_vals)
            move.post()
            notice.write({'account_move_id': move.id})

        return True

    def action_customer_move_create(self):
        notices_with_account_entries = self.filtered(lambda x: x.company_id.do_account_entries_for_customer_notice)
        #TODO: create account entries only for notices that require it
        return True

    def notice_line_move_line_get(self):
        self.ensure_one()

        res = []
        for line in self.notice_line_ids.filtered(lambda x: x.account_id and x.quantity):
            move_line_dict = {
                'type': 'src',
                'name': line.name,
                'price_unit': line.price_unit,
                'quantity': line.quantity,
                'price': line.price_subtotal,
                'account_id': line.account_id.id,
                'product_id': line.product_id.id,
                'uom_id': line.uom_id.id,
                'account_analytic_id': False,
                'analytic_tag_ids': False,
                'accounted_notice_line_id': line.id,
            }
            res.append(move_line_dict)
        return res

    def compute_notice_totals(self, imls):
        self.ensure_one()

        total = 0
        total_currency = 0
        diff_currency = self.currency_id and self.currency_id.id != self.company_currency_id.id and True or False
        company_currency = self.company_currency_id
        company = self.company_id
        currency = self.currency_id
        date = self.date or fields.Date.context_today(self)

        for line in imls:
            if diff_currency:
                if not (line.get('currency_id') and line.get('amount_currency')):
                    line['currency_id'] = currency.id
                    line['amount_currency'] = currency.round(line['price'])
                    line['price'] = currency._convert(line['price'], company_currency, company, date)
            else:
                line['currency_id'] = False
                line['amount_currency'] = False
                line['price'] = currency.round(line['price'])
            if self.type in ('out_notice', 'in_refund'):
                total += line['price']
                total_currency += line['amount_currency'] or line['price']
                line['price'] = - line['price']
            else:
                total -= line['price']
                total_currency -= line['amount_currency'] or line['price']
        return total, total_currency, imls

    def line_get_convert(self, iml, partner_id):
        return {
            'date_maturity': iml.get('date_maturity') or False,
            'partner_id': partner_id,
            'name': iml['name'][:64],
            'debit': iml['price'] > 0 and iml['price'],
            'credit': iml['price'] < 0 and abs(iml['price']),
            'account_id': iml['account_id'],
            'amount_currency': iml['price'] > 0 and abs(iml.get('amount_currency') or 0) or -1 * abs(iml.get('amount_currency') or 0),
            'currency_id': iml.get('currency_id') or False,
            'quantity': iml.get('quantity') or 1.00,
            'product_id': iml.get('product_id') or False,
            'product_uom_id': iml.get('uom_id') or False,
            'analytic_account_id': iml.get('account_analytic_id') or False,
            'accounted_notice_line_id': iml.get('accounted_notice_line_id') or False,
        }

    def finalize_note_move_lines(self, imls):
        return imls

    def _get_action_view_picking(self, pickings):
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_picking_tree_all")

        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            form_view = [(self.env.ref('stock.view_picking_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = pickings.id
        else:
            action['domain'] = [('id', '=', False)]
        action['context'] = {}

        return action

    def action_view_pickings(self):
        return self._get_action_view_picking(self.picking_ids)


class AccountNoticeLine(models.Model):
    _name = 'account.notice.line'
    _description = "Account Notice Line"

    @api.depends('price_unit', 'discount', 'quantity')
    def _compute_price(self):
        for line in self:
            line.price_unit_discounted = (line.price_unit or 0) * (1 - (line.discount or 0.0) / 100.0)
            line.price_subtotal = (line.quantity or 0) * line.price_unit_discounted

    name = fields.Text(string='Description', required=True)
    notice_id = fields.Many2one('account.notice', string='Notice Reference',
                                      ondelete='cascade', index=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure',
                             ondelete='set null', index=True)
    lot_id = fields.Many2one('stock.production.lot', string='Production lot',
                             ondelete='set null', index=True)
    product_id = fields.Many2one('product.product', string='Product',
                                 ondelete='restrict', index=True)
    price_unit = fields.Monetary(string='Unit Price', required=True)
    price_unit_discounted = fields.Monetary(string='Unit Price w Discount', store=True, readonly=True, compute='_compute_price')
    discount = fields.Float(string='Discount (%)')
    currency_id = fields.Many2one('res.currency', related='notice_id.currency_id', store=True)
    quantity = fields.Float(string='Quantity', digits='Product Unit of Measure', required=True)
    price_subtotal = fields.Monetary(string='Amount', store=True, readonly=True, compute='_compute_price')
    account_id = fields.Many2one('account.account', string='Account', domain=[('deprecated', '=', False)])
    product_qty = fields.Float('Product UOM Quantity', digits=0, compute='_compute_product_qty', inverse='_set_product_qty', store=True)
    invoice_line_id = fields.Many2one('account.move.line', string="Invoice Line", copy=False, help="Invoice Line related to this line. This is Invoice/Bill")
    account_move_line_id = fields.One2many('account.move.line', 'accounted_notice_line_id', string='Account Move Line', help="Account Move Line generated by this line. This is Account Move, not Invoice/Bill")

    @api.depends('product_id', 'uom_id', 'quantity')
    def _compute_product_qty(self):
        for line in self:
            line.product_qty = line.uom_id._compute_quantity(line.quantity, line.product_id.uom_id, rounding_method='HALF-UP')

    def _set_product_qty(self):
        """ The meaning of product_qty field changed lately and is now a functional field computing the quantity
        in the default product UoM. This code has been added to raise an error if a write is made given a value
        for `product_qty`, where the same write should set the `product_uom_qty` field instead, in order to
        detect errors. """
        raise UserError(_('The requested operation cannot be processed because of a programming error setting the `product_qty` field instead of the `quantity`.'))
