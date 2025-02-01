# -*- coding: utf-8 -*-
import base64
import requests
import zipfile
import logging
from lxml import etree

from datetime import datetime, timedelta
from odoo import _, fields, models, api

_logger = logging.getLogger(__name__)

class SPVVendorBill(models.Model):
    _name = "spv.vendor.bill"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "SPV Vendor Bill"

    # == Stored fields ==
    partner_id = fields.Many2one("res.partner", string="Partner")
    invoice_id = fields.Many2one('account.move', string="Vendor Bill Mapped")
    invoice_currency_id = fields.Many2one('res.currency', related="invoice_id.currency_id", string="Vendor Bill Mapped Currency", store=True)
    invoice_type = fields.Selection([('in_invoice', 'Vendor Bill'), ('in_refund', 'Refund')], string="Invoice Type", default="in_invoice")
    
    invoice_date = fields.Date(string='Vendor Bill Date')
    invoice_amount_total = fields.Monetary(string='Vendor Bill Total', currency_field="currency_id")
    invoice_amount_tax_total = fields.Monetary(string='Vendor Bill Tax Total', currency_field="currency_id")
    invoice_number = fields.Char('Vendor Bill')
    invoice_type_code = fields.Char('Type Code')
    invoice_currency_name = fields.Char(string="Vendor Bill Currency")
    currency_id = fields.Many2one('res.currency', string="Currency")
    partner_name = fields.Char('Supplier Name')
    
    partner_vat = fields.Char(string="Partner VAT")
    l10n_ro_edi_transaction = fields.Char(string="Transaction ID (RO)")
    l10n_ro_edi_download = fields.Char(string="Download ID (RO)")
    
    xml_attachment_id = fields.Many2one("ir.attachment", string="Request XML", copy=False,)
    xml_invoice_file = fields.Binary(string="XML", copy=False,)
    xml_invoice_filename = fields.Char(string="XML Filename", copy=False,)
    pdf_attachment_id = fields.Many2one("ir.attachment", string="PDF", copy=False,)
    
    state = fields.Selection(
        [("draft", "Draft"), ("xml_success", "XML Success"), ("xml_error", "XML Error"), ("pdf_success", "PDF Success"), ("pdf_error", "PDF Error"),],
        "State",
        copy=False,
        tracking=True,
        default='draft'
    )    
    notes = fields.Text()    
    communication = fields.Text()
    
    @api.model
    def create(self, vals):
#         if vals.get('partner_vat') and not vals.get('partner_id'):
#             partners = self.env['res.partner'].search([('vat', '=', vals['partner_vat'])], limit=1)
#             if partners:
#                 vals['partner_id'] = partners[0].id
                
        return super(SPVVendorBill, self).create(vals)
       
    def name_get(self):
        result = []
        for item in self:
            result.append((item.id, item.l10n_ro_edi_download or ''))
        return result

    def _get_invoice_search_domain(self):
        self.ensure_one()
        domain = []
        if self.partner_vat:
            domain.append(('partner_id.vat', '=', self.partner_vat))
        if self.invoice_number:
            domain.append(('ref', '=', self.invoice_number))
        return domain

    def _get_invoice_for_spv_bill(self):
        self.ensure_one()

        if self.invoice_id:
            return self.invoice_id

        domain = self._get_invoice_search_domain()
        if domain:
            return self.env['account.move'].search(domain, limit=1)
        return self.env['account.move']

    def _generate_invoice_for_spv_bill(self):
        self.ensure_one()

        invoice = self.env['account.move']

        try:
            if self.xml_invoice_file:
                content = base64.b64decode(self.xml_invoice_file)
                xml_tree = etree.fromstring(content)

                move_type = 'in_invoice'
                element = xml_tree.find('.//{*}InvoiceTypeCode')
                if element is not None and element.text == '381':
                    move_type = 'in_refund'

                invoice = invoice.with_context(default_move_type=move_type)
                journal = self._get_default_spv_bill_journal(invoice)
                invoice = invoice.with_context(default_journal_id=journal.id)

                invoice = self._import_ubl(xml_tree, invoice)
                if invoice:
                    for line in invoice.invoice_line_ids.filtered(lambda x: x.product_id):
                        line.write({'account_id': line._get_computed_account()})
                if invoice and self.pdf_attachment_id:
                    self.pdf_attachment_id.copy({'res_id': invoice.id, 'res_model': 'account.move'})
        except Exception as e:
            _logger.exception("Error when converting the xml content to etree: %s" % e)

        return invoice

    def _get_default_spv_bill_journal(self, invoice):
        return self.env.company.l10n_ro_spv_bill_journal_id or invoice._get_default_journal()

    def _import_ubl(self, tree, invoice):
        """ Decodes an UBL invoice into an invoice.

        :param tree:    the UBL tree to decode.
        :param invoice: the invoice to update or an empty recordset.
        :returns:       the invoice where the UBL data was imported.
        """

        def _get_ubl_namespaces():
            ''' If the namespace is declared with xmlns='...', the namespaces map contains the 'None' key that causes an
            TypeError: empty namespace prefix is not supported in XPath
            Then, we need to remap arbitrarily this key.

            :param tree: An instance of etree.
            :return: The namespaces map without 'None' key.
            '''
            namespaces = tree.nsmap
            namespaces['inv'] = namespaces.pop(None)
            return namespaces

        def _retrieve_tax(amount, type_tax_use):
            '''Search all taxes and find one that matches all of the parameters.

            :param amount:          The amount of the tax.
            :param type_tax_use:    The type of the tax.
            :returns:               A tax or an empty recordset if not found.
            '''
            domain = [
                ('amount', '=', float(amount)),
                ('type_tax_use', '=', type_tax_use),
                ('company_id', '=', self.env.company.id),
                ('is_for_spv_bills', '=', True)
            ]

            return self.env['account.tax'].search(domain, order='sequence ASC', limit=1)

        namespaces = _get_ubl_namespaces()

        EdiFormat = self.env['account.edi.format']

        journal = invoice.env.context.get('default_journal_id') and self.env['account.journal'].browse(invoice.env.context['default_journal_id']) or False

        def _find_value(xpath, element=tree):
            return EdiFormat._find_value(xpath, element, namespaces)

        vals = {}
        # Reference
        elements = tree.xpath('//cbc:ID', namespaces=namespaces)
        if elements:
            vals.update({'ref': elements[0].text})
        elements = tree.xpath('//cbc:InstructionID', namespaces=namespaces)
        if elements:
            vals.update({'payment_reference': elements[0].text})

        # Dates
        elements = tree.xpath('//cbc:IssueDate', namespaces=namespaces)
        if elements:
            vals.update({'invoice_date': elements[0].text})
        elements = tree.xpath('//cbc:PaymentDueDate', namespaces=namespaces)
        if elements:
            vals.update({'invoice_date_due': elements[0].text})
        # allow both cbc:PaymentDueDate and cbc:DueDate
        elements = tree.xpath('//cbc:DueDate', namespaces=namespaces)
        vals.update({'invoice_date_due': vals.get('invoice_date_due') or (elements and elements[0].text) or False})

        # Currency
        currency = EdiFormat._retrieve_currency(_find_value('//cbc:DocumentCurrencyCode'))
        if currency and currency.active:
            vals.update({'currency_id': currency.id})

        # Incoterm
        elements = tree.xpath('//cbc:TransportExecutionTerms/cac:DeliveryTerms/cbc:ID', namespaces=namespaces)
        if elements:
            incoterm = self.env['account.incoterms'].search([('code', '=', elements[0].text)], limit=1)
            vals.update({'invoice_incoterm_id': incoterm and incoterm.id})

        # Partner
        counterpart = 'Customer' if invoice.move_type in ('out_invoice', 'out_refund') else 'Supplier'
        partner = EdiFormat._retrieve_partner(
            name=_find_value(f'//cac:Accounting{counterpart}Party/cac:Party//cbc:Name'),
            phone=_find_value(f'//cac:Accounting{counterpart}Party/cac:Party//cbc:Telephone'),
            mail=_find_value(f'//cac:Accounting{counterpart}Party/cac:Party//cbc:ElectronicMail'),
            vat=_find_value(f'//cac:Accounting{counterpart}Party/cac:Party//cbc:CompanyID'),
        )
        vals.update({'partner_id': partner and partner.id or False})

        # Lines
        lines = []
        lines_elements = tree.xpath('//cac:InvoiceLine', namespaces=namespaces)
        for eline in lines_elements:
            line_vals = {}
            # Product
            elements =  eline.xpath('cac:Item/cbc:Name', namespaces=namespaces)
            line_name = elements and elements[0].text or False
            product = EdiFormat._retrieve_product(
                default_code=_find_value('cac:Item/cac:SellersItemIdentification/cbc:ID', eline),
                name=_find_value('cac:Item/cbc:Name', eline),
                barcode=_find_value('cac:Item/cac:StandardItemIdentification/cbc:ID[@schemeID=\'0160\']', eline)
            )
            line_vals.update({'product_id': product and product.id or False})

            # Quantity
            elements = eline.xpath('cbc:InvoicedQuantity', namespaces=namespaces)
            quantity = elements and float(elements[0].text) or 1.0
            line_vals.update({'quantity': quantity})

            # Price Unit
            elements = eline.xpath('cac:Price/cbc:PriceAmount', namespaces=namespaces)
            price_unit = elements and float(elements[0].text) or 0.0
            elements = eline.xpath('cbc:LineExtensionAmount', namespaces=namespaces)
            line_extension_amount = elements and float(elements[0].text) or 0.0
            line_vals.update({'price_unit': price_unit or line_extension_amount / quantity if quantity else 0.0})

            # Name
            elements = eline.xpath('cac:Item/cbc:Description', namespaces=namespaces)
            line_description = elements and elements[0].text or False
            line_vals.update({'name': "%s %s" % (line_name or '', line_description or '') if (line_name or line_description) else ((product and product.name_get()[0][1]) or line_name or _('description missing'))})

            # Taxes
            tax_ids = []
            tax_element = eline.xpath('cac:TaxTotal/cac:TaxSubtotal', namespaces=namespaces)
            for eline in tax_element:
                tax = _retrieve_tax(
                    amount=_find_value('cbc:Percent', eline),
                    type_tax_use=journal and journal.type or False
                )
                if tax:
                    tax_ids.append(tax.id)

            if not tax_ids:
                tax_element = eline.xpath('cac:Item/cac:ClassifiedTaxCategory', namespaces=namespaces)
                for eline in tax_element:
                    tax = _retrieve_tax(
                        amount=_find_value('cbc:Percent', eline),
                        type_tax_use=journal and journal.type or False
                    )
                    if tax:
                        tax_ids.append(tax.id)

            line_vals.update({'tax_ids': [(6, False, tax_ids)]})
            lines.append(line_vals)

        vals.update({'invoice_line_ids': [(0, False, line) for line in lines]})

        return invoice.create(vals)

    def _generate_invoices_from_spv_bill(self):
        res = {}
        for spv_bill in self.filtered(lambda x: not x.invoice_id):
            #1. Search odoo bill by partner CUI and invoice reference
            invoice = spv_bill._get_invoice_for_spv_bill()
            if not invoice:
                #2. No invoice is found then generate one and link it to this spv_bill
                invoice = spv_bill._generate_invoice_for_spv_bill()

            if invoice:
                res.update({spv_bill.id: invoice})

        return res

    def generate_invoice(self):
        res = self._generate_invoices_from_spv_bill()
        for spv_bill in self:
            if not res.get(spv_bill.id):
                continue

            spv_bill.write({'invoice_id': res[spv_bill.id].id})

        return True

    @api.model
    def _get_invoice_type_xml_tag_mapping(self):
        return {'Invoice': 'in_invoice', 'CreditNote': 'in_refund'}
       
    @api.model
    def _get_xml_paths(self):
        return {'cbc:ID': 'invoice_number',
                'cac:AccountingSupplierParty/cac:Party/cac:PartyLegalEntity/cbc:RegistrationName': 'partner_name',
                'cac:AccountingSupplierParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID': 'partner_vat',
                'cbc:IssueDate': 'invoice_date',
                'cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount': 'invoice_amount_total',
                'cac:TaxTotal/cbc:TaxAmount': 'invoice_amount_tax_total',
                'cbc:InvoiceTypeCode': 'invoice_type_code',
                'cbc:DocumentCurrencyCode': 'invoice_currency_name',
                }
       
    def _generate_items(self, items_dict):
        if not items_dict:
            return
           
        new_request_numbers = items_dict.keys()
        self.env.cr.execute("""SELECT array_agg(l10n_ro_edi_download) FROM spv_vendor_bill WHERE l10n_ro_edi_download IN %s""", (tuple(new_request_numbers),))
        res = self.env.cr.fetchone()
        
        to_create = []
        for request_number in new_request_numbers - (res and res[0] or []):
            if not items_dict.get(request_number):
                continue
               
            to_create += items_dict[request_number]
            
        return self.create(to_create) if to_create else False
       
    def _fetch_xml(self):
        """Response is: - json, if request has errors
        - binary (zip file), if request is successful
        """
        self.ensure_one()
        
        res = {}

        anaf_config = self.env.user.company_id.l10n_ro_account_anaf_sync_id
        if not anaf_config:
            return {"success": False, "error": _("Invalid Anaf Config"), "response": False}
           
        access_token = anaf_config.access_token

        url = anaf_config.anaf_einvoice_sync_url + "/descarcare"
        headers = {
            "Content-Type": "application/xml",
            "Authorization": "Bearer {0}".format(access_token),
        }
        params = {"id": self.l10n_ro_edi_download}
        response = False
        try:
            response = requests.get(url, params=params, headers=headers, timeout=80)
        except Exception as e:
            res = {"success": False, "error": str(e), "response": False}

        if response and response.status_code == 200:
            try:
                content_type = (
                    response.headers and response.headers["Content-Type"] or False
                )
                if content_type == "application/zip":
                    res = {"success": True, "response": response.content}
                elif content_type == "application/json":
                    answer = response.json()
                    if answer.get("eroare"):
                        res = {
                            "success": False,
                            "error": answer.get("eroare"),
                            "response": False,
                        }
                    else:
                        res = {
                            "success": False,
                            "error": _("Unknown response"),
                            "response": False,
                        }
            except Exception as e:
                res = {"success": False, "error": str(e), "response": False}
        elif response:
            res = {"success": False, "error": _("Access error"), "response": False}

        return res
       
    def _process_xml(self, fetch_response):
        self.ensure_one()
        
        vals = {"state": "xml_success"}
        if fetch_response.get("error"):
            vals.update(
                {
                    "state": "xml_error",
                    "communication": "{}<br/>{}".format(self.communication or "", fetch_response["error"]),
                }
            )
        elif fetch_response.get("response"):
            attachment = self.env["ir.attachment"].create(
                {
                    "name": _("ANAF Response.zip"),
                    "datas": base64.b64encode(fetch_response.get("response")),
                    "store_fname": _("ANAF Response.zip"),
                    "mimetype": "application/x-zip",
                    "res_model": self._name,
                    "res_id": self.id,
                }
            )
            vals.update({"xml_attachment_id": attachment.id})
            
            archive_full_path = attachment._full_path(attachment.store_fname)
            if zipfile.is_zipfile(archive_full_path):
                archive_xml_invoice_name = '{0}.xml'.format(self.l10n_ro_edi_transaction or _('Invoice'))
                with zipfile.ZipFile(archive_full_path) as myzip:
                    with myzip.open(archive_xml_invoice_name) as myfile:
                        vals.update({'xml_invoice_file': base64.b64encode(myfile.read()), 'xml_invoice_filename': archive_xml_invoice_name})

        self.write(vals)

        return True
       
    def _extract_xml(self):
        self.ensure_one()
        
        if not self.xml_invoice_file:
            return True
        
        map = self._get_invoice_type_xml_tag_mapping()
        xml_paths = self._get_xml_paths()
        vals = {'invoice_type': 'in_invoice'}
        try:  
            root = etree.fromstring(base64.b64decode(self.xml_invoice_file))
            root_tag = root.tag
            for tag_name, invoice_type in map.items():
                if root_tag and tag_name in root_tag:
                    vals.update({'invoice_type': invoice_type})
                    break
                   
            if xml_paths:
                for path, field_name in xml_paths.items():
                    tags = root.xpath(path, namespaces={'cbc': "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
                                                        'cac': "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
                                                        })
                    if tags:
                        vals.update({field_name: tags[0].text})
        except Exception as e:
            _logger.info('SPV Bills - extract xml error: %s' % str(e))
            pass

        if vals.get('invoice_currency_name'):
            # Currency
            currency = self.env['account.edi.format']._retrieve_currency(vals['invoice_currency_name'])
            if currency:
                vals.update({'currency_id': currency.id})

        self.write(vals)
        
        return True
        
    def _download_xml(self):
        for item in self:
            item._process_xml(item._fetch_xml())
            item._extract_xml()
            
        return True
       
    def _fetch_pdf(self):
        """Response is: - json, if request has errors
        - binary (zip file), if request is successful
        """
        self.ensure_one()
        
        res = {}

        anaf_config = self.env.user.company_id.l10n_ro_account_anaf_sync_id
        if not anaf_config:
            return True
           
        access_token = anaf_config.access_token

        #we'll just hardcode :(
        endpoint_for_invoice_type = 'FCN' if self.invoice_type == 'in_refund' else 'FACT1'
        #"https://webservicesp.anaf.ro/prod/FCTEL/rest/transformare/FCN" <-- for credit notes
        url = "https://webservicesp.anaf.ro/prod/FCTEL/rest/transformare/{0}".format(endpoint_for_invoice_type)
        headers = {
            "Content-Type": "text/plain",
            "Authorization": "Bearer {0}".format(access_token),
        }
        response = False
        try:
            response = requests.post(
                url, data=base64.b64decode(self.xml_invoice_file), headers=headers, timeout=80
            )
        except Exception as e:
            res = {"success": False, "error": str(e), "response": False}

        if response and response.status_code == 200:
            try:
                content_type = (
                    response.headers and response.headers["Content-Type"] or False
                )
                if content_type == "application/pdf":
                    res = {"success": True, "response": response.content}
                elif content_type == "application/json":
                    answer = response.json()
                    if answer.get("eroare"):
                        res = {
                            "success": False,
                            "error": answer.get("eroare"),
                            "response": False,
                        }
                    else:
                        res = {
                            "success": False,
                            "error": _("Unknown response"),
                            "response": False,
                        }
                else:
                    res = {"success": False, "error": _('Unknown response structure'), "response": False}
            except Exception as e:
                res = {"success": False, "error": str(e), "response": False}
        elif response:
            res = {"success": False, "error": _("Access error"), "response": False}

        return res
       
    def _process_pdf(self, fetch_response):
        self.ensure_one()
        
        vals = {"state": "pdf_success"}
        if fetch_response.get("error"):
            vals.update(
                {
                    "state": "pdf_error",
                    "communication": "{0}<br/>{1}".format(self.communication or "", fetch_response["error"]),
                }
            )
        elif fetch_response.get("response"):
            attachment_name = "{0}.pdf".format(self.xml_invoice_filename or _("Invoice"))
            attachment = self.env["ir.attachment"].create(
                {
                    "name": attachment_name,
                    "datas": base64.b64encode(fetch_response.get("response")),
                    "store_fname": attachment_name,
                    "mimetype": "application/x-pdf",
                    "res_model": self._name,
                    "res_id": self.id,
                }
            )
            vals.update({"pdf_attachment_id": attachment.id})

        self.write(vals)

        return True
       
    def _download_pdf(self):
        for item in self:
            item._process_pdf(item._fetch_pdf())
            
        return True

    @api.model
    def _cron_fetch_vendor_bills(self, days=1):
        params = {
            "cif": self.env.user.company_id.partner_id.vat.replace("RO", ""),
            "startTime": int((datetime.now() - timedelta(days=days)).timestamp()) * 1000,
            "endTime": int(datetime.now().timestamp()) * 1000,
            "filtru": "P",
        }

        page = 1
        res = self._fetch_vendor_bills_paged(params, page=page)

        while res.get('total_pages') > page:
            page += 1
            res = self._fetch_vendor_bills_paged(params, page=page)

        _logger.info('SPV Bills - vendor bills fetch completed')
        return res

    def _fetch_vendor_bills_paged(self, params, page=1):
        anaf_config = self.env.user.company_id.l10n_ro_account_anaf_sync_id
        if not anaf_config:
            return {'total_pages': 0, 'result': False}
        
        access_token = anaf_config.access_token
        url = anaf_config.anaf_einvoice_sync_url + "/listaMesajePaginatieFactura"
        headers = {
            "Authorization": "Bearer {0}".format(access_token),
        }
        params.update({"pagina": page})
        
        response = False
        try:
            response = requests.get(
                url, params=params, headers=headers, timeout=80
            )
        except Exception as e:
            _logger.info('SPV Bills - fetch vendor bills error: %s' % str(e))
            response = False
            
        res = False
        total_pages = 0
        if response and response.status_code == 200:
            try:
                content_type = (
                    response.headers and response.headers["Content-Type"] or False
                )
                if content_type == "application/json":
                    res = True
                    items = {}
                    answer = response.json()
                    if answer.get('eroare'):
                        _logger.info('SPV Bills - fetch vendor bills ANAF error: %s' % answer.get('eroare'))
                    for item in (answer.get('mesaje') or []):
                        if item.get('tip') != 'FACTURA PRIMITA':
                            continue
         
                        request_number = item.get('id') or False
                        items.setdefault(request_number, [])
                        items[request_number].append({'l10n_ro_edi_transaction': item.get('id_solicitare'),
                                                        'l10n_ro_edi_download': item.get('id'),
                                                        'notes': item.get('detalii')
                                                        })
                    self._generate_items(items)
                    total_pages = answer.get('numar_total_pagini') or 0
            except Exception as e:
                _logger.info('SPV Bills - fetch vendor bills error: %s' % str(e))
                res = False
        
        return {'total_pages': total_pages, 'result': res}
       
    @api.model
    def _cron_fetch_xml_vendor_bills(self, batch=10):
        if not batch:
            batch = 10
        items = self.search([('state', '=', 'draft'), ('l10n_ro_edi_download', '!=', False)], limit=batch)
        
        items._download_xml()
       
    @api.model
    def _cron_xml2pdf_vendor_bills(self, batch=10):
        if not batch:
            batch = 10
        items = self.search([('state', 'in', ['xml_success', 'pdf_error']), ('xml_invoice_file', '!=', False)], limit=batch)
        
        items._download_pdf()
        return True
       
