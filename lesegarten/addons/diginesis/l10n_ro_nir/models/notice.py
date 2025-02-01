# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang, format_amount


class AccountNotice(models.Model):
    _inherit = 'account.notice'
    _name = 'account.notice'

    def action_print_nir(self):
        if not self:
            return False

        pickings = self.env['stock.picking'].search([('notice_id', 'in', self.ids), ('state', '=', 'done')])
        return pickings.action_print_transfer()




