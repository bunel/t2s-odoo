# -*- coding: utf-8 -*-
import json
from lxml import etree
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from dateutil import rrule

from odoo import api, fields, models, _
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools.misc import formatLang
from odoo import tools

from odoo.exceptions import UserError, RedirectWarning, ValidationError

class AccountMove(models.Model):
	_inherit = "account.move"
		
	def cron_process_fancourier_slip(self, email_to, slip_date=None, send_mail=True):		
		self.process_fancourier_slip(email_to, (slip_date, slip_date), send_mail)
	 
	def process_fancourier_slip(self, email_to, slip_date=None, send_mail=True):
		
		DiginesisApiEndpoint = self.env['diginesis.api.endpoint']
		DiginesisDeliveryFancourier = self.env['diginesis.delivery.fancourier']		
		
		def register_payment(vals):
			""" TODO:    """			
			AccountPayment = self.env['account.payment']
			
			journal_id = self.env.company.fancourier_slip_journal_id
			if not journal_id:
				return False, _(u'Invalid FanCourier Slip journal'), False
			
			invoice = vals.get('invoice_id') or None	
			payment_type = invoice and invoice.residual > 0 and 'inbound' or 'outbound'
			payment_methods = payment_type == 'inbound' and journal.inbound_payment_method_ids or journal.outbound_payment_method_ids
			
			payment_vals = {
				'amount': vals.get('amount') or False,
				'payment_type': payment_type,		
				
				'journal_id': journal_id,				
				'payment_date': vals.get('slip_date', False),
				'payment_method_id': (payment_methods.ids + [False])[0],
				'invoice_ids': [(4, invoice and invoice.id or None)],
				'amount': vals.get('amount') or False,
				'currency_id': vals.get('currency_id') or False,
				'partner_id': vals.get('partner_id') or False,
				'partner_type': 'customer',
				'communication': invoice and invoice.number or False,
			}
			
			result = True
			message = ''
			payment = None
			try:
				payment = AccountPayment.create(payment_vals)
				if payment:
					payment.post()
				else:
					result = False
					
			except Exception as e:					
				result = False
				message = e.message				
				pass
			
			return result, message, payment
		
		items = [] 
		yesterday = fields.Date.today() - timedelta(days=1)		
		if slip_date is None:
			slip_date = (None, None)
		else:
			slip_date = tuple([isinstance(x, basestring) and fields.Date.from_string(x) or x for x in slip_date]) 
			
		slip_date = [x if x else yesterday for x in slip_date]		
		fancourier_api_credentials = DiginesisApiEndpoint.search([('import_slip', '=', True)])	
		
		if not fancourier_api_credentials:
			items.append(_("There are no Api Credentials for Slips."))
		else:
			date_range = list(rrule.rrule(rrule.DAILY, interval=1, dtstart=slip_date[0], until=slip_date[1]))
			for credentials in 	fancourier_api_credentials:
				for date_slip in date_range:
					parsed_date = date_slip.strftime("%d.%m.%Y")
					slip_data = DiginesisDeliveryFancourier.get_slip(credentials, date_slip)
					if not slip_data:
						items.append(_(u"{0}: There are no AWBs for credentials [{1}]").format(parsed_date, credentials.name))
					else:						
						awbs = DiginesisDeliveryFancourier.search([('awb', 'in', slip_data.keys())])
						loaded_awbs = dict((awb.awb, awb) for awb in awbs)
						for slip_awb in slip_data:
							awb_for_slip = loaded_awbs.get(slip_awb)
							awb_invoices = awb_for_slip and awb_for_slip.mapped('stock_picking_id.invoice_id')
							if not awb_invoices:
								items.append(_(u"{0}: AWB {1} - invoice cannot be found").format(parsed_date, slip_awb))
								continue 
							
							other_states = [state for state in awb_invoices.mapped('state') if state not in ['open']]
							if other_states:
								items.append(_(u"{0}: AWB {1} - invoice in status [{2}]").format(parsed_date, slip_awb, ','.join(other_states)))
								continue
							
							awb_invoice = awb_invoices[0]
							amount = slip_data[slip_awb].get('amount') or False
							try:
								float_amount = float(amount)
								payment_res, payment_message, payment = register_payment({'slip_date': date_slip, 
															'invoice_ids': awb_invoice, 
															'amount': float_amount, 
															'currency_id': awb_invoice.currency_id.id, 
															'partner_id': awb_invoice.commercial_partner_id.id})
								if payment_res: 
									items.append(_(u"{0}: AWB {1} - payment posted successfully").format(parsed_date, slip_awb))
									if payment:
										awb_for_slip.write({'payment_id': payment.id})
									else:
										items.append(_(u"{0}: AWB {1} - payment cannot be posted [{2}]").format(parsed_date, slip_awb, payment_message))
												
							except ValueError:										
								items.append(_(u"{0}: AWB {1} - invalid amount [{2}]").format(parsed_date, slip_awb, amount))
						
		if send_mail:
			template_values={			
				'process_results': u'<br/>'.join(items),
				'slip_date': "%s - %s" % tuple([x.strftime("%d.%m.%Y") for x in slip_date]),
			}
			self.send_reminder('fancourier_slip_process_result_template', template_values, email_to)
		else:
			return items
		
	 
	def send_reminder(self, template_name, replace_values, toAddress):		
		MailMail = self.env['mail.mail'].sudo()
		MailTemplate = self.env['mail.template']			
		template = self.env.ref('diginesis_delivery_fancourier.{0}'.format(template_name))
		
		result = True
		if template:			
			values = {'auto_delete': True,}
			for field in ['subject', 'body_html', 'email_to', 'email_from']:
				values[field] = MailTemplate._render_template(getattr(template, field), 'res.users', False) or False
			if not values['body_html']:
				values['body_html'] = ''	
			
			values['email_to'] = toAddress or values.get('email_to') or False			
			
			if values['body_html']:
				values['body_html'] = values['body_html'] % replace_values
				values['body'] = tools.html_sanitize(values['body_html'])
					
			if values['subject']:
				values['subject'] = values['subject'] % replace_values
							
			try:			
				MailMail.create(values).send()
			except Exception as e:
				result = False		
				pass
					
		return result	