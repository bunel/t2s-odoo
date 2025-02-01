# -*- coding: utf-8 -*-

from odoo import models, fields, _
from odoo.tools.safe_eval import safe_eval as eval
from odoo.exceptions import UserError
from datetime import date, datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
			
class DeliveryReportFancourier(models.TransientModel):	
	_name = "delivery.report.fancourier"
	_inherit = ['mail.thread']
	_description = "FanCourier Report"		
	
	def _default_status(self):		
		return self.env['diginesis.delivery.fancourier.status'].search([])
	
	date_from = fields.Date(string='Date From', default=fields.Date.context_today, required=True)
	date_to = fields.Date(string='Date To', default=fields.Date.context_today, required=True)	
	delivery_time_days = fields.Integer(string='Delivery Days')
	status_fancourier = fields.Many2many('diginesis.delivery.fancourier.status', 'delivery_report_fancourier_fancourier_status_rel', 'wizard_id', 'status_id',string='Status FanCourier', default=_default_status, required=True)	

	def action_generate_email_template(self):
		self.ensure_one()		
		
		hardcoded_delivered_status_code = '2'
		
		self.env.cr.execute("""SELECT id FROM diginesis_delivery_fancourier 
		WHERE date BETWEEN %s AND %s AND (no_compensation='f' OR no_compensation IS NULL) AND status_fancourier IN %s AND ((status_fancourier = %s AND delivery_time_days > %s) OR status_fancourier <> %s)
		""", (self.date_from, self.date_to, tuple(self.status_fancourier.mapped('code')), hardcoded_delivered_status_code, self.delivery_time_days, hardcoded_delivered_status_code))
		res = self.env.cr.fetchall()
		
		deliveries = self.env['diginesis.delivery.fancourier'].browse([x[0] for x in res])
		
		awb_by_status = dict((x.code, {'name': x.name, 'awb': []}) for x in self.status_fancourier)
		#Status FAN
		#- Nr awb, data confirmari (date),  <optional doar pentru livrat - Timp livrare: delivery_time_days zile>
		for delivery in deliveries:
			if not delivery.status_fancourier in awb_by_status:
				continue
			
			awb_by_status[delivery.status_fancourier]['awb'].append(_('- {0} - confirmed in {1} {2}').format(delivery.awb, delivery.date, delivery.status_fancourier in ['2'] and  _("- delivered in {0} days").format(delivery.delivery_time_days) or ''))
		
		body = []
		for status in awb_by_status:			
			res = awb_by_status[status]
			if len(res['awb']) > 0:
				body.append(u"<strong>{0}</strong><br/><p style='margin-left: 10px;'>{1}</p>".format(res['name'], '<br/>'.join(res['awb'])))			
			
		template = self.env.ref('diginesis_delivery_fancourier.fancourier_send_report_fancourier_email_template', False)
		compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
		
		ctx = dict(
			default_model='delivery.report.fancourier',
			default_res_id=self.id,
			default_use_template=bool(template),
			default_template_id=template.id,
			default_composition_mode='comment',
			awb_status_text = awb_by_status,
			body = u'<br/>'.join(body),
		)
		return {
			'name': _('Compose Email'),
			'type': 'ir.actions.act_window',
			'view_mode': 'form',
			'res_model': 'mail.compose.message',
			'views': [(compose_form.id, 'form')],
			'view_id': compose_form.id,
			'target': 'new',
			'context': ctx,
		}