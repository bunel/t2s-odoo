# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from odoo.tools.misc import formatLang, format_date


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = "account.move"

    def _post(self, soft=True):
        moves = self.filtered(lambda move: move.is_purchase_document() and not move.ref)
        if moves:
            raise ValidationError(_('Please fill in the bill number of the Supplier Bill Reference'))

        return super(AccountMove, self)._post(soft=soft)

    @api.constrains('ref', 'move_type', 'partner_id', 'journal_id', 'invoice_date', 'state')
    def _check_duplicate_supplier_reference(self):
        moves = self.filtered(lambda move: move.state == 'posted' and move.is_purchase_document() and move.ref)
        if not moves:
            return

        self.env["account.move"].flush([
            "ref", "move_type", "invoice_date", "journal_id",
            "company_id", "partner_id", "commercial_partner_id",
        ])
        self.env["account.journal"].flush(["company_id"])
        self.env["res.partner"].flush(["commercial_partner_id"])

        # /!\ Computed stored fields are not yet inside the database.
        self._cr.execute('''
                   SELECT move2.id
                   FROM account_move move
                   JOIN account_journal journal ON journal.id = move.journal_id
                   JOIN res_partner partner ON partner.id = move.partner_id
                   INNER JOIN account_move move2 ON
                       move2.ref = move.ref
                       AND move2.company_id = journal.company_id
                       AND move2.commercial_partner_id = partner.commercial_partner_id
                       AND move2.move_type = move.move_type                       
                       AND move2.id != move.id
                   WHERE move.id IN %s
               ''', [tuple(moves.ids)])
        duplicated_moves = self.browse([r[0] for r in self._cr.fetchall()])
        if duplicated_moves:
            raise ValidationError(
                _('Duplicated vendor reference detected. You probably encoded twice the same vendor bill/credit note:\n%s') % "\n".join(
                    duplicated_moves.mapped(lambda m: "%(partner)s - %(ref)s - %(date)s" % {
                        'ref': m.ref,
                        'partner': m.partner_id.display_name,
                        'date': format_date(self.env, m.invoice_date),
                    })
                ))