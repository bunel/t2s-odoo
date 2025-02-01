# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, format_datetime
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.tools.misc import format_date

NOTICE_TYPE_FROM_PICKING = {'supplier|internal': 'in_notice',
                            'internal|supplier': 'in_refund',
                            'internal|customer': 'out_notice',
                            'customer|internal': 'out_refund',
                            'internal|internal': 'internal'}


class Picking(models.Model):
    _inherit = "stock.picking"

    notice_id = fields.Many2one('account.notice', string="Notice", copy=False)
