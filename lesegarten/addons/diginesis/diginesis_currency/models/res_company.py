from odoo import api, fields, models, tools, _
import time
from datetime import datetime
import logging
import string
import ssl
import sys,traceback
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError

from lxml import etree
from urllib.request import urlopen

_logger = logging.getLogger(__name__)

_intervalTypes = {
    'work_days': lambda interval: relativedelta(days=interval),
    'days': lambda interval: relativedelta(days=interval),
    'hours': lambda interval: relativedelta(hours=interval),
    'weeks': lambda interval: relativedelta(days=7*interval),
    'months': lambda interval: relativedelta(months=interval),
    'minutes': lambda interval: relativedelta(minutes=interval),
}

class Company(models.Model):
	_name = 'res.company'
	_inherit = 'res.company'
	
	#date.isoweekday(): Return the day of the week as an integer, where Monday is 1 and Sunday is 7
	DAYS_NOT_VERIFY_UPDATE_CURRENCY = [6,7]
	
	auto_update_currencies = fields.Boolean(compute='_get_auto_update_currencies', inverse='_save_auto_update_currencies',
												string='Automatic update of the currencies', store=False,
												default=lambda obj:obj._get_auto_update_currencies())
	update_currency_ids = fields.Many2many('res.currency', 'res_company_currency_rel', 'company_id', 'currency_id', 'Currencies to update for this company',)
	start_date = fields.Datetime(compute='_get_start_date', inverse='_save_start_date', string='Start date time', store=False, required=False,
								default=lambda obj:obj._get_start_date())
	interval_number = fields.Integer(compute='_get_interval_number', inverse='_save_interval_number', string='Service update frequency', store=False, 
									required=False,default=lambda obj:obj._get_interval_number())
	interval_type = fields.Selection(compute='_get_interval_type', inverse='_save_interval_type', string='Service update frequency type',
								 selection= [('minutes', 'Minutes'),
											('hours', 'Hours'),
											('work_days','Work Days'),
											('days', 'Days'),
											('weeks', 'Weeks'),
											('months', 'Months')],
								 help="Set this value to define the update frequency.", store=False, required=True,
								 default=lambda obj:obj._get_interval_type())
	currency_update_log_ids = fields.One2many('currency.rate.update.log', compute='_log_ids', string='Currency update log')	
	currency_update_main_currency_name = fields.Char('Main Currency Name', help="Currency name as it appears in data to be imported", default="RON")
	currency_update_endpoint = fields.Char('XML Endpoint', help="Url to data to be imported", default="https://www.bnr.ro/nbrfxrates.xml")
	
	@api.model
	def get_update_cron(self):		
		return self.env.ref('diginesis_currencies_rates_update.ir_cron_auto_currency_update', False) or False

	@api.model
	def get_retry_update_cron(self):
		return self.env.ref('diginesis_currencies_rates_update.ir_cron_auto_retry_currency_update', False) or False
		
	@api.model
	def save_update_cron(self, values):
		cron = self.get_update_cron()
		return cron and cron.write(values) or False		

	@api.model
	def save_retry_update_cron(self, values):		
		cron = self.get_retry_update_cron()
		return cron and cron.write(values) or False

	def _get_auto_update_currencies(self):		
		ctx = (self.env.context or {}).copy()
		ctx['active_test'] = False		
		
		update_cron = self.get_update_cron()
		read = update_cron and update_cron.with_context(ctx).read(['active']) or False
		for company in self:	
			company.auto_update_currencies = read and read[0] and read[0]['active'] or False
			
	def _save_auto_update_currencies(self):
		ctx = (self.env.context or {}).copy()
		ctx['active_test'] = False	
		
		return self.with_context(ctx).save_update_cron({'active':self.auto_update_currencies})

	def _get_start_date(self):		
		ctx = (self.env.context or {}).copy()
		ctx['active_test'] = False		
		
		update_cron = self.get_update_cron()
		read = update_cron and update_cron.with_context(ctx).read(['nextcall']) or False
		for company in self:	
			company.start_date = read and read[0] and read[0]['nextcall'] or False

	def _save_start_date(self):		
		ctx = (self.env.context or {}).copy()
		ctx['active_test'] = False
		return self.with_context(ctx).save_update_cron({'nextcall':self.start_date})

	def _get_interval_number(self):
		ctx = (self.env.context or {}).copy()	
		ctx['active_test'] = False		
		
		update_cron = self.get_update_cron()
		read = update_cron and update_cron.with_context(ctx).read(['interval_number']) or False
		for company in self:	
			company.interval_number = read and read[0] and read[0]['interval_number'] or False

	@api.model
	def _get_retry_interval_number(self):
		ctx = (self.env.context or {}).copy()	
		ctx['active_test'] = False		
				
		retry_update_cron = self.get_retry_update_cron()
		read = retry_update_cron and retry_update_cron.with_context(ctx).read(['interval_number'])
		return  read and read[0] and read[0]['interval_number'] or False

	def _save_interval_number(self):
		ctx = (self.env.context or {}).copy()
		ctx['active_test'] = False
		
		return self.with_context(ctx).save_update_cron({'interval_number':self.interval_number})		

	def _get_interval_type(self):
		ctx = (self.env.context or {}).copy()	
		ctx['active_test'] = False		
		
		update_cron = self.get_update_cron()
		read = update_cron and update_cron.with_context(ctx).read(['interval_type']) or False
		for company in self:	
			company.interval_type = read and read[0] and read[0]['interval_type'] or False

	@api.model
	def _get_retry_interval_type(self):
		ctx = (self.env.context or {}).copy()	
		ctx['active_test'] = False		
				
		update_cron = self.get_retry_update_cron()
		read = update_cron and update_cron.read(['interval_type']) or False
		return read and read[0] and read[0]['interval_type'] or False

	def _save_interval_type(self):
		ctx = (self.env.context or {}).copy()
		ctx['active_test'] = False
		
		return self.with_context(ctx).save_update_cron({'interval_type':self.interval_type})

	@api.model
	def _get_retry_numbercall(self):
		ctx = (self.env.context or {}).copy()	
		ctx['active_test'] = False		
				
		update_cron = self.get_retry_update_cron()
		read = update_cron and update_cron.read(['numbercall']) or False
		return read and read[0] and read[0]['numbercall'] or False

	def _log_ids(self):
		Log = self.env['currency.rate.update.log']
		for company in self:
			company.currency_update_log_ids = Log.search([('company_id', '=', company.id)], limit=20, order='date desc, id asc')

	@api.model
	def _activate_retry_cron(self):
		retry_interval_number = self._get_retry_interval_number()
		retry_interval_type = self._get_retry_interval_type()
		retry_update_date = datetime.utcnow()
		retry_update_date += _intervalTypes[retry_interval_type](retry_interval_number)
		return self.save_retry_update_cron({'active': True, 'nextcall': retry_update_date.strftime('%Y-%m-%d %H:%M:%S'), 'numbercall': 4})

	@api.model
	def _deactivate_retry_cron(self):
		return self.save_retry_update_cron({'active': False})
	
	def action_refresh_currencies(self):
		"""Refresh  the currencies"""
		try:
			self.update_curencies()
		except Exception as e:
			_logger.exception(str(e))			

	def update_company_currency(self):
		self.ensure_one()
		
		ResCurrency = self.env['res.currency']
		ResCurrencyRate = self.env['res.currency.rate']
			
		log_messages = []
		result = True
		try :
			curr_to_fetch = [x.name.upper() for x in self.update_currency_ids]
			
			res, log_info, rate_name = self.get_updated_currencies(curr_to_fetch)			
			if rate_name:
				if res:
					currency_rates_to_create = []
					for currency in self.update_currency_ids:
						if currency.name not in res:
							log_messages.append("Currency {0} not found therefore not updated".format(currency.name))
							continue
						
						self.env.cr.execute("""SELECT count(id) FROM res_currency_rate WHERE currency_id=%s AND name=%s""", (currency.id, rate_name))
						currency_rate_res = self.env.cr.fetchone()
						
						if (not currency_rate_res or not currency_rate_res[0]) and res[currency.name] > 0:
							currency_rates_to_create.append({
										'currency_id': currency.id,
										'rate':( 1 / res[currency.name]),
										'name': rate_name})
					
					if currency_rates_to_create:
						self.env['res.currency.rate'].create(currency_rates_to_create)
					
					log_messages.append('Currencies updated')
				else:
					log_messages.append("There are no currency rates to update")
			else:
				log_messages.append("Currencies updated: missing rate date, given {0}".format(rate_name or ''))

			expected_rate_name = fields.Date.today().strftime('%Y-%m-%d')
			result = (expected_rate_name == rate_name) and True or False

		except Exception as e:
			exc_type, exc_value, exc_traceback = sys.exc_info()
			_logger.info(str(e) + repr(traceback.format_exception(exc_type, exc_value, exc_traceback)))
			
			log_messages.append(str(e))
			result = False

		if log_messages:
			self.env['currency.rate.update.log'].create([dict(name=mess,date=fields.Datetime.now(),company_id=self.id) for mess in log_messages])
							
		return result

	@api.model
	def update_curencies(self):
		res = self.env.company.update_company_currency()
		if res:
			self._deactivate_retry_cron()
		else:
			self._activate_retry_cron()

	@api.model
	def retry_update_currencies(self, email=None):
		company = self.env.company	
		res = company.update_company_currency()
		if res:
			self._deactivate_retry_cron()
		else:
			if self._get_retry_numbercall() == 1:
				company.verify_currency_update(email)
		
	def verify_currency_update(self, email=None):		
		current_day_number = datetime.now().isoweekday()
		if current_day_number in self.DAYS_NOT_VERIFY_UPDATE_CURRENCY:
			return True
		
		ResCurrencyRate = self.env['res.currency.rate']
		rate_name = fields.Date.today().strftime('%Y-%m-%d')

		for company in self:
			main_curr = company._get_main_currency_name()
			try :
				not_updated_currencies = []
				for currency in company.update_currency_ids.filtered(lambda x: x.name != main_curr):
					if ResCurrencyRate.search_count([('currency_id','=', currency.id), ('name','=', rate_name)]) <= 0:
						not_updated_currencies.append(currency.name)
						
			except Exception as e:
				exc_type, exc_value, exc_traceback = sys.exc_info()
				
				_logger.info(str(e) + repr(traceback.format_exception(exc_type, exc_value, exc_traceback)))
				
				msg_subj = "ERROR when verifying currency updates"
				msg_body = msg_subj +": " + (str(e))
				
				self.send_message(email, msg_subj, msg_body)

			if not_updated_currencies > 0:
				self.send_message(email, "Currency(s) {0} not updated".format(', '.join(not_updated_currencies)))
				
		return True

	def send_message(self, email, subject, body=None):
		if not email:
			return
						
		if not body:
			body = subject
			
		values = {
			'model': None,
			'res_id': None,
			'subject': subject,
			'body_html': body,
			'parent_id': None,
			'auto_delete': True,
			'email_to': email,
		}
				
		try:
			self.env['mail.mail'].sudo().create(values).send()
		except Exception as e:
			_logger.info('Update Currency Rate: email cannot be sent')		

	def rate_retrieve(self, node) :
		""" Parse a dom node to retrieve 
		currencies data"""
		res = {}
		if isinstance(node, list) :
			if len(node) > 0 :
				node = node[0]
		res['code'] = node.attrib['currency'].upper()
		res['rate_currency'] = float(node.text)
		res['rate_ref'] = 1.0
		if 'multiplier' in node.attrib:
			res['rate_ref'] = float(node.attrib['multiplier'])

		return res

	def get_updated_currencies(self, currency_array):
		self.ensure_one()
		
		#'http://www.bnr.ro/nbrfxrates.xml'
		url = self.env.company.currency_update_endpoint
		main_currency_name = self.env.company._get_main_currency_name()
		
		if not url or not main_currency_name:
			raise Exception(_('Please configure Currency Rate Update parameters'))
			
		# We do not want to update the main currency
		if main_currency_name in currency_array :
			currency_array.remove(main_currency_name)

		rawfile = self.get_url(url)		
		_logger.info(rawfile)
		
		dom = etree.XML(rawfile)
		ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
		ssl_context.set_ciphers('DEFAULT')
		root = etree.parse(urlopen(url, context=ssl_context)).getroot()
		
		log_info = " "
		main_rate = 0.0
		date_name = False
		
		for node in dom.findall('.//{http://www.bnr.ro/xsd}Rate'):
			if node.attrib['currency'].upper() == main_currency_name:
				tmp_data = self.rate_retrieve(node)
				main_rate = tmp_data['rate_currency'] / tmp_data['rate_ref']

		updated_currencies = {}
		for node in dom.findall('.//{http://www.bnr.ro/xsd}Rate'):
			if node.attrib['currency'].upper() in currency_array:
				tmp_data = self.rate_retrieve(node)
				rate = 0
				if main_rate > 0.0 :
					rate = (tmp_data['rate_currency'] / tmp_data['rate_ref']) / main_rate
				else:
					rate = tmp_data['rate_currency'] / tmp_data['rate_ref']

				updated_currencies[tmp_data['code']] = rate

		for el in dom.getiterator('{http://www.bnr.ro/xsd}Cube'):
			date_name = datetime.strptime(el.attrib['date'], '%Y-%m-%d')
			date_name = date_name and date_name.strftime('%Y-%m-%d') or False			
			
		return updated_currencies, log_info, date_name

	@api.model
	def get_url(self, url):
		"""Return a string of a get url query"""
		rawfile = False
		try:
			ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
			ssl_context.set_ciphers('DEFAULT')
			objfile = urlopen(url, context=ssl_context)
			rawfile = objfile.read()
			objfile.close()				
		except IOError as ex:
			_logger.log(logging.INFO, 'Update Currency Rate: Web Service does not exist !')
			
		return rawfile
	
	def _get_main_currency_name(self):
		self.ensure_one()
		
		main_currency_name = self.currency_update_main_currency_name
		return main_currency_name and main_currency_name.upper() or main_currency_name

class CurrencyRateUpdateLog(models.Model):
	_name = "currency.rate.update.log"
	_description = "Currency rate update log"
	_order = 'date desc, id asc'
	
	name = fields.Char('Name', required=True)
	date = fields.Datetime('Date', required=True)
	company_id = fields.Many2one('res.company', 'Company', required=True, index=True, ondelete='cascade')
	