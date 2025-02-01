# -*- coding: utf-8 -*-

from odoo import models, fields, _
from odoo.tools.safe_eval import safe_eval as eval
from odoo.exceptions import UserError
from datetime import date, datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF

class DeliverySlipFancourier(models.TransientModel):
	_name = "delivery.slip.fancourier"
	_description = "FanCourier Slip"
	
	slip_date_from = fields.Date(string='Slip Date From', default=fields.Date.context_today, required=True)
	slip_date_to = fields.Date(string='Slip Date To', default=fields.Date.context_today, required=True)	
	message = fields.Text(string='Message')
	
	def get_fancourier_slip_action(self):
		
		self.ensure_one()		
		
		res = self.env['account.invoice'].process_fancourier_slip(None, slip_date=(self.slip_date_from, self.slip_date_to), send_mail=False)		
		self.write({'message': "\n".join(res)})
				
		result = self.env.ref('diginesis_delivery_fancourier.action_slip_fancourier').read()[0]		
		result['res_id'] = self.id
		
		return result	