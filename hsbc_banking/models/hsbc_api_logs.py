# -*- coding: utf-8 -*-

from odoo import models, fields
from lxml import etree


class HsbcApiLogs(models.Model):
    _name = 'hsbc.api.log'

    name = fields.Char()
    batch_ref = fields.Char()
    response_ref = fields.Char()
    payments_ids = fields.Many2many('hsbc.account.payment', 'hsbc_logs_payments_rel', string="HSBC Payments")
    date_sent = fields.Datetime(string="Sent Date")
    date_respond = fields.Datetime(string="Response Date")
    request_header = fields.Char('Request Header')
    request_xml = fields.Char('Request XML')
    response = fields.Char('Response')
    response_data = fields.Char('Response Data')
    failure_stack = fields.Char(default='N/A')
    verified = fields.Boolean()
    type = fields.Selection([
        ('bulk_init', 'Bulk Payment Transaction (FDET)'),
        ('pay_enquiry', 'Payment Status Enquiry'),
    ])
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('fail', 'Failed'),
        ('done', 'Done'),
        ('pro', 'Processed')
    ], string='Status', default='draft')

    def process_pay_status(self):
        logs = self.env['hsbc.api.log'].search([
            ('type', '=', 'pay_enquiry'),
            ('state', '=', 'done'),
            ('response_data', '!=', ''),
        ])
        for log in logs:
            pay_status_dict = {}
            root = etree.XML(log.response_data.encode())
            for element in root.iter():
                tag_name = etree.QName(element).localname
                if tag_name == 'OrgnlEndToEndId':
                    c_endid = element.text
                elif tag_name == 'TxSts':
                    sts = element.text
                elif tag_name == 'AddtlInf':
                    inf = element.text
                    pay_status_dict.update({
                        'tr_id': c_endid,
                        'status': sts,
                        'info': inf,
                    })
                    break
            hsbc_payment_id = None
            if log.payments_ids and log.payments_ids[0].transaction_refs.find(pay_status_dict['tr_id']) != -1:
                hsbc_payment_id = log.payments_ids[0]
            if hsbc_payment_id:
                # Required actual codes and their corresponding meaning
                pass
                # if pay_status_dict['status'] == 'ACCP':
                #     hsbc_payment_id.state = 'approved'
                #     if hsbc_payment_id.account_payment.state == 'draft':
                #         hsbc_payment_id.account_payment.hsbc_trigger = True
                #         hsbc_payment_id.account_payment.action_post()
                #     hsbc_payment_id.account_payment.write({
                #         'hsbc_status': 'approved',
                #         'utr_ref': pay_status_dict['info']
                #     })
                # else:
                #     hsbc_payment_id.state = 'declined'
                #     hsbc_payment_id.account_payment.hsbc_status = 'rejected'
