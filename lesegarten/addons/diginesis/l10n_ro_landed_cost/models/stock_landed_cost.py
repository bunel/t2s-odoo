# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_is_zero, float_round


SPLIT_METHOD = [
    ('by_value', ' By Value'),
    ('by_weight', 'By Weight'),
    ('by_volume', 'By Volume'),
]


class L10nROStockLandedCost(models.Model):
    _name = 'l10n.ro.stock.landed.cost'
    _description = 'Stock Landed Cost'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _default_account_journal_id(self):
        """Take the journal configured in the company, else fallback on the stock journal."""
        lc_journal = self.env['account.journal']
        if self.env.company.lc_journal_id:
            lc_journal = self.env.company.lc_journal_id
        else:
            lc_journal = self.env['ir.property']._get("property_stock_journal", "product.category")
        return lc_journal

    name = fields.Char(
        'Name', default=lambda self: _('New'),
        copy=False, readonly=True, tracking=True)
    date = fields.Date(
        'Date', default=fields.Date.context_today,
        copy=False, required=True, readonly=True, states={'draft': [('readonly', False)]}, tracking=True)
    target_model = fields.Selection(
        [('picking', 'Transfers')], string="Apply On",
        required=True, default='picking',
        copy=False, readonly=True, states={'draft': [('readonly', False)]})
    picking_ids = fields.Many2many(
        'stock.picking', string='Transfers',
        copy=False, readonly=True, states={'draft': [('readonly', False)]})
    notice_ids = fields.Many2many('account.notice', 'account_notice_l10n_ro_stock_landed_cost_rel', 'l10n_ro_stock_landed_cost_id', 'account_notice_id',
                                    string="Notice", copy=False, readonly=True, states={'draft': [('readonly', False)]}, domain=[('type', '=', 'in_notice')])
    bill_ids = fields.Many2many('account.move', 'account_move_l10n_ro_stock_landed_cost_rel', 'l10n_ro_stock_landed_cost_id', 'account_move_id',
                                string="Invoices", copy=False, readonly=True, states={'draft': [('readonly', False)]}, domain=[('move_type', '=', 'in_invoice')])
    cost_lines = fields.One2many(
        'l10n.ro.stock.landed.cost.lines', 'cost_id', 'Cost Lines',
        copy=True, readonly=True, states={'draft': [('readonly', False)]})
    valuation_adjustment_lines = fields.One2many(
        'l10n.ro.stock.valuation.adjustment.lines', 'cost_id', 'Valuation Adjustments',
        readonly=True, states={'draft': [('readonly', False)]})
    description = fields.Text(
        'Item Description', readonly=True, states={'draft': [('readonly', False)]})
    amount_total = fields.Monetary(
        'Total', compute='_compute_total_amount',
        store=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Posted'),
        ('cancel', 'Cancelled')], 'State', default='draft',
        copy=False, readonly=True, tracking=True)
    account_move_id = fields.Many2one(
        'account.move', 'Journal Entry',
        copy=False, readonly=True)
    account_journal_id = fields.Many2one(
        'account.journal', 'Account Journal',
        required=True, readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self._default_account_journal_id())
    company_id = fields.Many2one('res.company', string="Company",
        related='account_journal_id.company_id')
    vendor_bill_ids = fields.Many2many(
        'account.move', 'landed_cost_vendor_bill_rel', 'landed_cost_id', 'vendor_bill_id',
        'Vendor Bill', copy=False, domain=[('move_type', '=', 'in_invoice')], readonly=True, states={'draft': [('readonly', False)]},  help="Vendor Bill with Landed Cost")
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    def init(self):
        self._cr.execute("""
                ALTER TABLE account_notice_l10n_ro_stock_landed_cost_rel DROP CONSTRAINT IF EXISTS account_notice_uniq;
                ALTER TABLE account_notice_l10n_ro_stock_landed_cost_rel ADD CONSTRAINT account_notice_uniq UNIQUE (account_notice_id);
                
                ALTER TABLE account_move_l10n_ro_stock_landed_cost_rel DROP CONSTRAINT IF EXISTS account_move_uniq;
                ALTER TABLE account_move_l10n_ro_stock_landed_cost_rel ADD CONSTRAINT account_move_uniq UNIQUE (account_move_id);
                """)


    @api.depends('cost_lines.price_unit')
    def _compute_total_amount(self):
        for cost in self:
            cost.amount_total = sum(line.price_unit for line in cost.cost_lines)

    @api.onchange('target_model')
    def _onchange_target_model(self):
        if self.target_model != 'picking':
            self.picking_ids = False

    @api.onchange('notice_ids', 'bill_ids')
    def _onchange_notice_invoice_ids(self):
        pickings = self.env['stock.picking']
        if self.bill_ids:
            pickings |= self.env['stock.picking'].search([('vendorbill_id', 'in', self.bill_ids.ids), ('state', '=', 'done')])
        if self.notice_ids:
            pickings |= self.env['stock.picking'].search([('notice_id', 'in', self.notice_ids.ids), ('state', '=', 'done')])

        self.picking_ids = pickings

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('stock.landed.cost')
        return super().create(vals)

    def unlink(self):
        self.button_cancel()
        return super().unlink()

    def _track_subtype(self, init_values):
        if 'state' in init_values and self.state == 'done':
            return self.env.ref('l10n_ro_landed_cost.mt_stock_landed_cost_open')
        return super()._track_subtype(init_values)

    def button_cancel(self):
        account_moves = self.mapped('account_move_id').with_context(force_delete=True)
        account_moves.mapped('line_ids').remove_move_reconcile()
        account_moves.button_draft()
        account_moves.unlink()

        valuation_adjustment_lines = self.mapped('valuation_adjustment_lines').filtered(lambda line: line.move_id)
        valuation_adjustment_lines._cancel()

        return self.write({'state': 'cancel'})

    def button_cancel_draft(self):
        return self.write({'state': 'draft'})

    def button_validate(self):
        self._check_can_validate()
        cost_without_adjusment_lines = self.filtered(lambda c: not c.valuation_adjustment_lines)
        if cost_without_adjusment_lines:
            cost_without_adjusment_lines.compute_landed_cost()
        if not self._check_sum():
            raise UserError(_('Cost and adjustments lines do not match. You should maybe recompute the landed costs.'))

        for cost in self:
            cost = cost.with_company(cost.company_id)
            move = self.env['account.move']
            move_vals = {
                'journal_id': cost.account_journal_id.id,
                'date': cost.date,
                'ref': cost.name,
                'line_ids': [],
                'move_type': 'entry',
            }
            valuation_adjustment_lines = cost.valuation_adjustment_lines.filtered(lambda line: line.move_id)
            for line in valuation_adjustment_lines:
                qty_out = 0
                move_vals['line_ids'] += line._create_accounting_entries(move, qty_out)

            # We will only create the accounting entry when there are defined lines (the lines will be those linked to products of real_time valuation category).
            cost_vals = {'state': 'done'}
            if move_vals.get("line_ids"):
                move = move.create(move_vals)
                cost_vals.update({'account_move_id': move.id})
            cost.write(cost_vals)
            if cost.account_move_id:
                move._post()

            valuation_adjustment_lines._validate()

            posted_vendor_bills = cost.vendor_bill_ids and cost.vendor_bill_ids.filtered(lambda x: x.state == 'posted') or False
#            if posted_vendor_bills and cost.company_id.anglo_saxon_accounting:
#                all_amls = posted_vendor_bills.mapped('line_ids') | cost.account_move_id.line_ids
#                for product in cost.cost_lines.product_id:
#                    accounts = product.product_tmpl_id.get_product_accounts()
#                    input_account = accounts['stock_input']
#                    all_amls.filtered(lambda aml: aml.account_id == input_account and not aml.reconciled).reconcile()

        return True

    def get_valuation_lines(self):
        self.ensure_one()
        lines = []

        for move in self._get_targeted_move_ids():
            # it doesn't make sense to make a landed cost for a product that isn't set as being valuated in real time at real cost
            if move.product_id.cost_method not in ('fifo', 'average') or move.state == 'cancel' or not move.product_qty:
                continue
            accounts = move.product_id.product_tmpl_id._get_product_accounts()
            vals = {
                'product_id': move.product_id.id,
                'move_id': move.id,
                'quantity': move.product_qty,
                'former_cost': sum(move.stock_valuation_layer_ids.mapped('value')),
                'weight': move.product_id.weight * move.product_qty,
                'volume': move.product_id.volume * move.product_qty,
                'diff_account_id': accounts['expense'].id or False
            }
            lines.append(vals)

        if not lines:
            target_model_descriptions = dict(self._fields['target_model']._description_selection(self.env))
            raise UserError(_("You cannot apply landed costs on the chosen %s(s). Landed costs can only be applied for products with FIFO or average costing method.", target_model_descriptions[self.target_model]))
        return lines

    def compute_landed_cost(self):
        AdjustementLines = self.env['l10n.ro.stock.valuation.adjustment.lines']
        AdjustementLines.search([('cost_id', 'in', self.ids)]).unlink()

        self._check_cost()

        towrite_dict = {}
        for cost in self.filtered(lambda cost: cost._get_targeted_move_ids()):
            rounding = cost.currency_id.rounding
            total_qty = 0.0
            total_cost = 0.0
            total_weight = 0.0
            total_volume = 0.0
            total_line = 0.0
            all_val_line_values = cost.get_valuation_lines()
            for val_line_values in all_val_line_values:
                for cost_line in cost.cost_lines:
                    val_line_values.update({'cost_id': cost.id, 'cost_line_id': cost_line.id})
                    self.env['l10n.ro.stock.valuation.adjustment.lines'].create(val_line_values)
                total_qty += val_line_values.get('quantity', 0.0)
                total_weight += val_line_values.get('weight', 0.0)
                total_volume += val_line_values.get('volume', 0.0)

                former_cost = val_line_values.get('former_cost', 0.0)
                # round this because former_cost on the valuation lines is also rounded
                total_cost += cost.currency_id.round(former_cost)

                total_line += 1

            for line in cost.cost_lines:
                value_split = 0.0
                for valuation in cost.valuation_adjustment_lines:
                    value = 0.0
                    if valuation.cost_line_id and valuation.cost_line_id.id == line.id:
                        if line.split_method == 'by_weight' and total_weight:
                            per_unit = (line.price_unit / total_weight)
                            value = valuation.weight * per_unit
                        elif line.split_method == 'by_volume' and total_volume:
                            per_unit = (line.price_unit / total_volume)
                            value = valuation.volume * per_unit
                        elif line.split_method == 'by_value' and total_cost:
                            per_unit = (line.price_unit / total_cost)
                            value = valuation.former_cost * per_unit
                        else:
                            value = (line.price_unit / total_line)

                        if rounding:
                            value = tools.float_round(value, precision_rounding=rounding, rounding_method='UP')
                            fnc = min if line.price_unit > 0 else max
                            value = fnc(value, line.price_unit - value_split)
                            value_split += value

                        if valuation.id not in towrite_dict:
                            towrite_dict[valuation.id] = value
                        else:
                            towrite_dict[valuation.id] += value
        for key, value in towrite_dict.items():
            AdjustementLines.browse(key).write({'additional_landed_cost': value})
        return True

    def _get_targeted_move_ids(self):
        return self.picking_ids.move_lines

    def _check_can_validate(self):
        if any(cost.state != 'draft' for cost in self):
            raise UserError(_('Only draft landed costs can be validated'))
        for cost in self:
            if not cost._get_targeted_move_ids():
                target_model_descriptions = dict(self._fields['target_model']._description_selection(self.env))
                raise UserError(_('Please define %s on which those additional costs should apply.', target_model_descriptions[cost.target_model]))

    def _check_sum(self):
        """ Check if each cost line its valuation lines sum to the correct amount
        and if the overall total amount is correct also """
        prec_digits = self.env.company.currency_id.decimal_places
        for landed_cost in self:
            total_amount = sum(landed_cost.valuation_adjustment_lines.mapped('additional_landed_cost'))
            if not tools.float_is_zero(total_amount - landed_cost.amount_total, precision_digits=prec_digits):
                return False

            val_to_cost_lines = defaultdict(lambda: 0.0)
            for val_line in landed_cost.valuation_adjustment_lines:
                val_to_cost_lines[val_line.cost_line_id] += val_line.additional_landed_cost
            if any(not tools.float_is_zero(cost_line.price_unit - val_amount, precision_digits=prec_digits)
                   for cost_line, val_amount in val_to_cost_lines.items()):
                return False
        return True

    def _check_cost(self):
        negative_cost_lines = self.mapped('cost_lines').filtered(lambda x: x.price_unit < 0)
        if negative_cost_lines:
            raise UserError("\n".join([_('Please check {0}. You can not allocate negative amounts.').format(l.name or '') for l in negative_cost_lines]))
        return True


class L10nROStockLandedCostLine(models.Model):
    _name = 'l10n.ro.stock.landed.cost.lines'
    _description = 'Stock Landed Cost Line'

    name = fields.Char('Description')
    cost_id = fields.Many2one(
        'l10n.ro.stock.landed.cost', 'Landed Cost',
        required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    price_unit = fields.Monetary('Cost', required=True)
    split_method = fields.Selection(
        SPLIT_METHOD,
        string='Split Method',
        required=True,
        help="By Value : Cost will be divided according to product's value.\n"
             "By Weight : Cost will be divided depending on its weight.\n"
             "By Volume : Cost will be divided depending on its volume.")
    account_id = fields.Many2one('account.account', 'Account', domain=[('deprecated', '=', False)])
    currency_id = fields.Many2one('res.currency', related='cost_id.currency_id')

    @api.onchange('product_id')
    def onchange_product_id(self):
        self.name = self.product_id.name or ''
        self.split_method = self.product_id.product_tmpl_id.split_method_landed_cost or self.split_method or 'by_value'
        self.price_unit = self.product_id.standard_price or 0.0
        accounts_data = self.product_id.product_tmpl_id.get_product_accounts()
        self.account_id = accounts_data['expense']


class L10nROAdjustmentLines(models.Model):
    _name = 'l10n.ro.stock.valuation.adjustment.lines'
    _description = 'Valuation Adjustment Lines'

    name = fields.Char(
        'Description', compute='_compute_name', store=True)
    cost_id = fields.Many2one(
        'l10n.ro.stock.landed.cost', 'Landed Cost',
        ondelete='cascade')
    cost_line_id = fields.Many2one(
        'l10n.ro.stock.landed.cost.lines', 'Cost Line', readonly=True)
    move_id = fields.Many2one('stock.move', 'Stock Move', readonly=True)
    product_id = fields.Many2one('product.product', 'Product', required=True)
    quantity = fields.Float(
        'Quantity', default=1.0,
        digits=0, required=True)
    weight = fields.Float(
        'Weight', default=1.0,
        digits='Stock Weight')
    volume = fields.Float(
        'Volume', default=1.0, digits='Volume')
    former_cost = fields.Monetary(
        'Original Value')
    additional_landed_cost = fields.Monetary(
        'Additional Landed Cost')
    final_cost = fields.Monetary(
        'New Value', compute='_compute_final_cost',
        store=True)
    currency_id = fields.Many2one('res.currency', related='cost_id.company_id.currency_id')
    price_unit_additional = fields.Float("Price Unit Additional", digits="Product Price", compute="_compute_price_unit_additional", store=True)
    rounding_difference = fields.Float("Round Diff", compute="_compute_price_unit_additional", store=True)
    diff_account_id = fields.Many2one('account.account', string="Difference Account")

    @api.depends('cost_line_id.name', 'product_id.code', 'product_id.name')
    def _compute_name(self):
        for line in self:
            name = '%s - ' % (line.cost_line_id.name if line.cost_line_id else '')
            line.name = name + (line.product_id.code or line.product_id.name or '')

    @api.depends('former_cost', 'additional_landed_cost')
    def _compute_final_cost(self):
        for line in self:
            line.final_cost = line.former_cost + line.additional_landed_cost

    @api.depends('additional_landed_cost', 'quantity')
    def _compute_price_unit_additional(self):
        precision = self.env['decimal.precision'].precision_get('Product Price')
        for line in self:
            if line.quantity:
                pua = float_round((line.additional_landed_cost or 0) / line.quantity, precision_digits=precision)
                temp_alc = line.currency_id.round(line.quantity * pua)
                line.rounding_difference = (line.additional_landed_cost or 0) - temp_alc
                line.price_unit_additional = pua
            else:
                line.price_unit_additional = 0
                line.rounding_difference = 0

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            accounts = self.product_id.product_tmpl_id._get_product_accounts()
            self.diff_account_id = accounts['expense'] or False
        else:
            self.diff_account_id = False

    def _create_accounting_entries(self, move, qty_out):
        self.ensure_one()

        cost_product = self.cost_line_id.product_id
        if not cost_product:
            return False

        svl_account_ids = self.move_id.mapped('stock_valuation_layer_ids.account_id').ids if self.move_id.stock_valuation_layer_ids else False
        accounts = self.product_id.product_tmpl_id.get_product_accounts()
        debit_account_id = svl_account_ids and svl_account_ids[0] or accounts.get('stock_valuation') and accounts['stock_valuation'].id or False
        # If the stock move is dropshipped move we need to get the cost account instead the stock valuation account
        if self.move_id._is_dropshipped():
            debit_account_id = accounts.get('expense') and accounts['expense'].id or False

        already_out_account_id = accounts['stock_output'].id

        cost_product_accounts = cost_product.product_tmpl_id.get_product_accounts()
        credit_account_id = self.cost_line_id.account_id.id or (cost_product_accounts.get('expense') and cost_product_accounts.get('expense').id) or False

        if not credit_account_id:
            raise UserError(_('Please configure Expense Account for product: %s.') % (cost_product.name))

        if self.rounding_difference != 0 and not self.diff_account_id:
            raise UserError(_('Please configure Difference Account for valuation adjustment of product: %s.') % (self.product_id.name_get()[0][1]))

        return self._create_account_move_line(move, credit_account_id, debit_account_id, qty_out, already_out_account_id)

    def _create_account_move_line(self, move, credit_account_id, debit_account_id, qty_out, already_out_account_id):
        """
        Generate the account.move.line values to track the landed cost.
        Afterwards, for the goods that are already out of stock, we should create the out moves
        """
        AccountMoveLine = []

        base_line = {
            'name': self.name,
            'product_id': self.product_id.id,
            'quantity': 0,
        }
        debit_line = dict(base_line, account_id=debit_account_id)
        credit_line = dict(base_line, account_id=credit_account_id)
        diff = self.additional_landed_cost
        if diff > 0:
            debit_line['debit'] = diff
            credit_line['credit'] = diff
        else:
            # negative cost, reverse the entry
            debit_line['credit'] = -diff
            credit_line['debit'] = -diff
        AccountMoveLine.append([0, 0, debit_line])
        AccountMoveLine.append([0, 0, credit_line])

        if self.rounding_difference != 0 and self.diff_account_id:
            r_diff = self.rounding_difference
            debit_line = dict(base_line, account_id=self.diff_account_id.id)
            credit_line = dict(base_line, account_id=debit_account_id)

            if r_diff > 0:
                debit_line['debit'] = r_diff
                credit_line['credit'] = r_diff
            else:
                debit_line['credit'] = -r_diff
                credit_line['debit'] = -r_diff

            AccountMoveLine.append([0, 0, debit_line])
            AccountMoveLine.append([0, 0, credit_line])

        return AccountMoveLine

    def _validate(self):
        stock_receptions = self.mapped('move_id.stock_valuation_layer_ids.stock_reception_id')
        stock_receptions.write({'to_update': True})

    def _cancel(self):
        stock_receptions = self.mapped('move_id.stock_valuation_layer_ids.stock_reception_id')
        stock_receptions.write({'to_update': True})


