# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError, AccessError
from odoo.tools import float_is_zero, float_compare
from itertools import groupby


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = "sale.order"

    notice_count = fields.Integer(string='Notice Count', compute='_count_notices')

    def _prepare_notice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()

        notice_vals = {
            'currency_id': self.pricelist_id.currency_id.id,
            'incoterm_id': self.incoterm and self.incoterm.id or False,
            'reference': self.client_order_ref,
        }
        return notice_vals

    def _count_notices(self):
        for sale in self:
            sale.notice_count = len(sale._get_notices())

    def _get_notices(self):
        return self.mapped('picking_ids.notice_id') | self.mapped('picking_ids.outgoing_notice_id')

    def action_view_notice(self):
        return self._get_action_view_notice(self._get_notices())

    def _get_action_view_notice(self, notices):
        self.ensure_one()

        action = self.env["ir.actions.actions"]._for_xml_id("account_notice.action_notice_customer_tree")

        if len(notices) > 1:
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

    def _create_invoices(self, grouped=False, final=False, date=None):
        """
        Overrides the entire original method (sale > sale_order.py > _create_invoices). There is no other way.

        Create the invoice associated to the SO.
        :param grouped: if True, invoices are grouped by SO id. If False, invoices are grouped by
                        (partner_invoice_id, currency)
        :param final: if True, refunds will be generated if necessary
        :returns: list of created invoices
        """
        if not self.env['account.move'].check_access_rights('create', False):
            try:
                self.check_access_rights('write')
                self.check_access_rule('write')
            except AccessError:
                return self.env['account.move']

        notices_to_invoice = self.env['account.notice']
        pickings_to_invoice = {}

        # 1) Create invoices.
        invoice_vals_list = []
        invoice_item_sequence = 0 # Incremental sequencing to keep the lines order on the invoice.
        for order in self:
            order = order.with_company(order.company_id)
            pickings_to_invoice.setdefault(order.id, self.env['stock.picking'])

            invoice_vals = order._prepare_invoice()
            invoiceable_lines = order._get_invoiceable_lines(final)

            if not any(not line.display_type for line in invoiceable_lines):
                continue

            invoice_line_vals = []
            for line in invoiceable_lines:
                if line.is_downpayment:
                    continue
                if line.product_id and line.product_id.detailed_type == 'service':
                    invoice_line_vals.append(
                        (0, 0, line._prepare_invoice_line(
                            sequence=invoice_item_sequence,
                        )),
                    )
                    invoice_item_sequence += 1
                else:
                    done_moves = line.mapped('move_ids').filtered(lambda x: x.state == 'done' and x.mapped('move_line_ids.notice_line_ids.notice_id'))
                    notices = done_moves.mapped('move_line_ids.notice_line_ids.notice_id')

                    if line.noticed_to_invoice_qty and notices:
                        """
                        Avizele nefacturate - se adaga pe linia de factura la descriere 
                        (se cauta toate avizele legate de livrari DONE ale acestei linii de SO - care nu sunt in status invoiced). 
                        Daca nu se gaseste niciunul - se iau cele in stats invoiced (toate).
                        """

                        done_pickings = done_moves.mapped('picking_id').filtered(lambda x: not x.invoice_id)
                        not_invoiced_notices = notices.filtered(lambda x: x.state not in ['invoice', 'cancel'])
                        line_notices = not_invoiced_notices or notices.filtered(lambda x: x.state in ['invoice'])

                        prepared_invoice_line = line._prepare_invoice_line(
                                sequence=invoice_item_sequence,
                                quantity=line.noticed_to_invoice_qty
                            )
                        line_values_to_update = {'name': line._post_prepare_invoice_line_name(
                                                            prepared_invoice_line,
                                                            {
                                                                'notice_name': ", ".join([x for x in line_notices.mapped('name') if x]),
                                                                'picking_name': ", ".join([x for x in done_pickings.mapped('name') if x]),
                                                                'invoice_line_name': prepared_invoice_line.get('name') or False
                                                            }
                                                        )
                                                }
                        prepared_invoice_line.update(line_values_to_update)

                        invoice_line_vals.append(
                            (0, 0, prepared_invoice_line),
                        )
                        invoice_item_sequence += 1
                        notices_to_invoice |= not_invoiced_notices
                        pickings_to_invoice[order.id] |= done_pickings

                    if line.unnoticed_to_invoice_qty:
                        """
                        Livrarile ne-avizate - se adaga pe linia de factura la descriere (se cauta toate livrarile acestei linii de de SO care nu au aviz)
                        """
                        picking_disallowed_states = ['cancel']
                        picking_allowed_states = []
                        if line.product_id.invoice_policy == 'delivery':
                            picking_allowed_states.append('done')

                        line_moves = line.mapped('move_ids').filtered(lambda x: not x.mapped('move_line_ids.notice_line_ids.notice_id'))
                        line_pickings = line_moves.mapped('picking_id').filtered(lambda x: not x.invoice_id and x.state not in picking_disallowed_states and
                                                                                            (x.state in picking_allowed_states if picking_allowed_states else True))
                        prepared_invoice_line = line._prepare_invoice_line(
                                sequence=invoice_item_sequence,
                                quantity=line.unnoticed_to_invoice_qty
                            )
                        line_values_to_update = {'name': line._post_prepare_invoice_line_name(
                                                            prepared_invoice_line, {
                                                                                    'picking_name': ", ".join([x for x in line_pickings.mapped('name') if x]),
                                                                                    'invoice_line_name': prepared_invoice_line.get('name') or False
                                                                                    })}
                        prepared_invoice_line.update(line_values_to_update)

                        invoice_line_vals.append(
                            (0, 0, prepared_invoice_line),
                        )
                        invoice_item_sequence += 1
                        pickings_to_invoice[order.id] |= line_pickings

            invoice_vals['invoice_line_ids'] += invoice_line_vals
            invoice_vals_list.append(invoice_vals)

        if not invoice_vals_list:
            raise self._nothing_to_invoice_error()

        # 2) Manage 'grouped' parameter: group by (partner_id, currency_id).
        if not grouped:
            new_invoice_vals_list = []
            invoice_grouping_keys = self._get_invoice_grouping_keys()
            invoice_vals_list = sorted(
                invoice_vals_list,
                key=lambda x: [
                    x.get(grouping_key) for grouping_key in invoice_grouping_keys
                ]
            )
            for grouping_keys, invoices in groupby(invoice_vals_list, key=lambda x: [x.get(grouping_key) for grouping_key in invoice_grouping_keys]):
                origins = set()
                payment_refs = set()
                refs = set()
                ref_invoice_vals = None
                for invoice_vals in invoices:
                    if not ref_invoice_vals:
                        ref_invoice_vals = invoice_vals
                    else:
                        ref_invoice_vals['invoice_line_ids'] += invoice_vals['invoice_line_ids']
                    origins.add(invoice_vals['invoice_origin'])
                    payment_refs.add(invoice_vals['payment_reference'])
                    refs.add(invoice_vals['ref'])
                ref_invoice_vals.update({
                    'ref': ', '.join(refs)[:2000],
                    'invoice_origin': ', '.join(origins),
                    'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
                })
                new_invoice_vals_list.append(ref_invoice_vals)
            invoice_vals_list = new_invoice_vals_list

        # 3) Create invoices.

        # As part of the invoice creation, we make sure the sequence of multiple SO do not interfere
        # in a single invoice. Example:
        # SO 1:
        # - Section A (sequence: 10)
        # - Product A (sequence: 11)
        # SO 2:
        # - Section B (sequence: 10)
        # - Product B (sequence: 11)
        #
        # If SO 1 & 2 are grouped in the same invoice, the result will be:
        # - Section A (sequence: 10)
        # - Section B (sequence: 10)
        # - Product A (sequence: 11)
        # - Product B (sequence: 11)
        #
        # Resequencing should be safe, however we resequence only if there are less invoices than
        # orders, meaning a grouping might have been done. This could also mean that only a part
        # of the selected SO are invoiceable, but resequencing in this case shouldn't be an issue.
        if len(invoice_vals_list) < len(self):
            SaleOrderLine = self.env['sale.order.line']
            for invoice in invoice_vals_list:
                sequence = 1
                for line in invoice['invoice_line_ids']:
                    line[2]['sequence'] = SaleOrderLine._get_invoice_line_sequence(new=sequence, old=line[2]['sequence'])
                    sequence += 1

        # Manage the creation of invoices in sudo because a salesperson must be able to generate an invoice from a
        # sale order without "billing" access rights. However, he should not be able to create an invoice from scratch.
        moves = self.env['account.move'].sudo().with_context(default_move_type='out_invoice').create(invoice_vals_list)

        # 4) Mark notices and pickings as invoiced
        if notices_to_invoice:
            notices_to_invoice.write({'state': 'invoice'})

        for order in self:
            if pickings_to_invoice.get(order.id):
                moves_for_order = order.invoice_ids.filtered(lambda x: x.id in moves.ids)
                if not moves_for_order:
                    continue
                pickings_to_invoice[order.id].write({'invoice_id': moves_for_order[0].id})

        # 5) Some moves might have downpayment; deduct downpayments
        if final:
            for order in self.filtered(lambda x: any(l.is_downpayment for l in x.order_line)):
                prec = order.currency_id.decimal_places
                moves_for_order = order.invoice_ids.filtered(lambda x: x.id in moves.ids)
                if not moves_for_order:
                    continue

                move_for_order = moves_for_order[0]
                invoiced_amount = move_for_order.amount_total

                downpayment_lines = order.order_line.filtered(lambda x: x.is_downpayment)
                main_downpayment_lines = downpayment_lines.filtered(lambda x: not x.original_downpayment_line_id)

                if float_compare(sum([l.price_unit for l in downpayment_lines]), 0, precision_digits=prec) <= 0:
                    continue

                downpayment_groups = dict((l.id, {'main': l, 'all': l}) for l in main_downpayment_lines)
                for dl in downpayment_lines - main_downpayment_lines:
                    orig_id = (dl.mapped('original_downpayment_line_id.id') + [False])[0]
                    if orig_id and downpayment_groups.get(orig_id):
                        downpayment_groups[orig_id]['all'] |= dl

                downpayment_invoice_lines = []
                for dg in downpayment_groups.values():
                    if float_compare(invoiced_amount, 0, precision_digits=prec) <= 0:
                        break
                    main_downpayment_line = dg.get('main')
                    dg_amount = sum([l.price_unit for l in dg.get('all')])
                    if float_compare(dg_amount, 0, precision_digits=prec) <= 0:
                        continue

                    todo_amount = min(dg_amount, invoiced_amount)
                    invoiced_amount -= todo_amount

                    downpayment_invoice_lines.append(
                            (0, 0, main_downpayment_line._prepare_invoice_line(
                                sequence=invoice_item_sequence,
                                price_unit=todo_amount,
                                quantity=-1
                            )),
                        )
                    invoice_item_sequence += 1

                    main_downpayment_line.copy(default={'price_unit': -todo_amount,
                                                         'original_downpayment_line_id': main_downpayment_line.id,
                                                         'order_id': main_downpayment_line.order_id.id,
                                                         'state': main_downpayment_line.state,
                                                         })

                if downpayment_invoice_lines:
                    move_for_order.write({'invoice_line_ids': downpayment_invoice_lines})

        for move in moves:
            move.message_post_with_view('mail.message_origin_link',
                values={'self': move, 'origin': move.line_ids.mapped('sale_line_ids.order_id')},
                subtype_id=self.env.ref('mail.mt_note').id
            )
        return moves
