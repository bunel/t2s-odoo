# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import http, _
from odoo.http import request
from odoo.modules.module import get_resource_path
from odoo.osv import expression
from odoo.tools import pdf, split_every
from odoo.tools.misc import file_open


class ToledoRepairBarcodeController(http.Controller):

    @http.route('/toledo_repair_barcode/scan_from_main_menu', type='json', auth='user')
    def main_menu(self, barcode, **kw):
        """ Receive a barcode scanned from the main menu and return the appropriate
            action or warning.
        """
        ret_open_serial = self._try_open_serial(barcode)
        if ret_open_serial:
            return ret_open_serial

        return {'warning': _('There is no serial number corresponding to barcode %(barcode)s') % {'barcode': barcode}}

    def _try_open_serial(self, barcode):
        """ If barcode represents a picking, open it
        """
        action = request.env['ir.actions.act_window']._for_xml_id('diginesis_warranty.diginesis_serial_number_tree_action')
        serial_id = False
        try:
            serial_id = int(barcode)
        except:
            pass

        action['res_id'] = serial_id
        return {'action': action}
