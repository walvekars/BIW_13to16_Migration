from odoo import models, fields
from odoo.exceptions import ValidationError
from . import hsbc_api
import traceback


class HsbcAccountPayment(models.Model):
    _name = 'hsbc.account.payment'

    account_payment = fields.Many2one('account.payment', string="Payment")
    all_logs = fields.Many2many('hsbc.api.log', string='ALL logs')  # compute
    partners = fields.Many2one('res.partner', string='Partners', related='account_payment.partner_id')
    hsbc_users = fields.Many2one('res.users', string='Users')
    amount = fields.Float(string="Amount")
    create_time = fields.Datetime(string='Create Time')
    transaction_refs = fields.Char()
    state = fields.Selection([
        ('request_pending', 'Request Pending'),
        ('request_sent', 'Request Sent'),
        ('approved', 'Approved'),
        ('declined', 'Declined'),
        ('expired', 'Expired'),
        ('failed', 'Failed'),
        ('cancel', 'Cancelled'),
    ], string="Status")
    errors_log = fields.Text('Errors Log')

    def confirm_hsbc_payments(self):
        self.env['hsbc.account.payment'].initiate_bulk_transaction()
        print("donenoneno")

    def initiate_bulk_transaction(self):
        print("Inside bulk")
        selected_ids = self.env.context.get('active_ids', [])
        hsbc_payments = self.env['hsbc.account.payment'].browse(selected_ids)

        if hsbc_payments:
            valid_hsbc_payments = self.env['hsbc.account.payment']
            partners_list = []
            total_amount = 0
            transaction_seq = self.env.ref('hsbc_banking.hsbc_bulk_transaction_seq')  # .next_by_id()
            transaction_refs = []
            for hsbc_rec in hsbc_payments:
                # for partner in partners:
                rec = hsbc_rec.account_payment
                try:
                    partner_dict = {
                        'name': rec.partner_id.name,
                        'addr1': rec.partner_id.street2[:16],
                        'addr2': rec.partner_id.street[:16],
                        'zip': rec.partner_id.zip,
                        'city': rec.partner_id.city,
                        'state': rec.partner_id.state_id.name,
                        'country_code': rec.partner_id.country_id.code,
                        'amount': str(rec.amount),
                        'bank_name': rec.partner_bank_id.bank_id.name,
                        'ifsc': rec.partner_bank_id.bank_id.bic,
                        'acc_no': rec.partner_bank_id.acc_number,
                    }
                except Exception as e:
                    hsbc_rec.errors_log = f"{hsbc_rec.errors_log}\n{fields.datetime.now()}{e}\n\nStack Trace-\n{traceback.format_exc()}"
                    continue
                partners_list.append(partner_dict)
                total_amount += rec.amount
                t_id = transaction_seq.next_by_id()
                transaction_refs.append(t_id)
                if not hsbc_rec.transaction_refs:
                    hsbc_rec.transaction_refs = f"{t_id};"
                else:
                    hsbc_rec.transaction_refs += f"{t_id};"
                valid_hsbc_payments += hsbc_rec
            if valid_hsbc_payments:
                company = self.env.company
                company_dict = {
                    'name': company.name,
                    'addr1': company.street2[:16],
                    'addr2': company.street[:16],
                    'zip': company.zip,
                    'city': company.city,
                    'country_code': company.country_id.code,
                    'amount': str(total_amount),
                    'bank_name': 'HSBC Bank',
                    'ifsc': 'HSBCINBB',
                    'acc_no': '073560500001',
                }
                params = {
                    'url': self.env['ir.config_parameter'].sudo().get_param('hsbc.api.url', False),
                    'client_id': self.env['ir.config_parameter'].sudo().get_param('hsbc.client.id', False),
                    'client_secret': self.env['ir.config_parameter'].sudo().get_param('hsbc.client.secret', False),
                    'profile_id': self.env['ir.config_parameter'].sudo().get_param('hsbc.profile.id', False),
                    'payload_type': self.env['ir.config_parameter'].sudo().get_param('hsbc.payload.type', False),
                    'private_key': self.env['ir.config_parameter'].sudo().get_param('biw.private.key', False),
                    'public_key': self.env['ir.config_parameter'].sudo().get_param('hsbc.public.key', False),
                    'pass': self.env['ir.config_parameter'].sudo().get_param('biw.key.passphrase', False),
                }
                data_params = {
                    'transaction_refs': transaction_refs,
                }
                bulk_log = self.env['hsbc.api.log'].sudo().create([{
                    'type': 'bulk_init',
                    'payments_ids': [(6, 0, valid_hsbc_payments.ids)],
                    'date_sent': fields.Datetime.now(),
                    'request_header': str(params),
                    'state': 'draft',
                }])
                for pay in valid_hsbc_payments:
                    pay.write({'all_logs': [(4, bulk_log.id)]})
                try:
                    msg_id, batch_ref, data_xml, response, ref, decrypted_response, verified = hsbc_api.bulk_payments_api(
                        company_dict, partners_list, params, data_params
                    )
                    bulk_log.write({
                        'name': msg_id,
                        'response_ref': ref,
                        'batch_ref': batch_ref,
                        'request_xml': data_xml,
                        'response': response.content.decode(),
                        'response_data': decrypted_response,
                        'verified': verified,
                        'date_respond': fields.Datetime.now(),
                        'state': 'done',
                    })
                    if decrypted_response:
                        valid_hsbc_payments.state = 'request_sent'
                        valid_hsbc_payments.mapped('account_payment').write({'hsbc_status': 'sent'})
                except Exception as e:
                    bulk_log.write({
                        'name': "Failed On" + str(fields.Datetime.now()),
                        'state': 'fail',
                        'failure_stack': traceback.format_exc(),
                        'response': str(e),
                    })
                hsbc_rec.state = 'request_sent'
                print("end of bulk")


    def get_payment_status(self):
        hsbc_payments = self.env['hsbc.account.payment'].search([('state', '=', 'request_sent')])
        if hsbc_payments:
            params = {
                'url': self.env['ir.config_parameter'].sudo().get_param('hsbc.payments.status.api.url', False),
                'client_id': self.env['ir.config_parameter'].sudo().get_param('hsbc.client.id', False),
                'client_secret': self.env['ir.config_parameter'].sudo().get_param('hsbc.client.secret', False),
                'profile_id': self.env['ir.config_parameter'].sudo().get_param('hsbc.profile.id', False),
                'payload_type': self.env['ir.config_parameter'].sudo().get_param('hsbc.payload.type', False),
                'private_key': self.env['ir.config_parameter'].sudo().get_param('biw.private.key', False),
                'public_key': self.env['ir.config_parameter'].sudo().get_param('hsbc.public.key', False),
                'pass': self.env['ir.config_parameter'].sudo().get_param('biw.key.passphrase', False),
            }
        for payment in hsbc_payments:
            transaction_ref = payment.transaction_refs
            j = 1
            for i in range(2, len(transaction_ref) + 1):
                if transaction_ref[-i] == ';':
                    j = i
                    break
            last_ref = transaction_ref[-j + 1:-1]
            last_pay_log = payment.all_logs.filtered(lambda log: log.type == 'bulk_init')[-1]
            batch_ref = last_pay_log.batch_ref
            response_ref = last_pay_log.response_ref
            status_log = self.env['hsbc.api.log'].sudo().create([{
                'type': 'pay_enquiry',
                'payments_ids': [(6, 0, payment.ids)],
                'date_sent': fields.Datetime.now(),
                'request_header': str(params),
                'state': 'draft',
            }])
            payment.write({'all_logs': [(4, status_log.id)]})
            if last_ref and batch_ref and response_ref:
                try:
                    msg_id, batch_ref, data_xml, response, ref, decrypted_response, verified = \
                        hsbc_api.payments_status_enquiry_api(params, last_ref, batch_ref, response_ref)
                    status_log.write({
                        'name': msg_id,
                        'response_ref': ref,
                        'batch_ref': batch_ref,
                        'request_xml': data_xml,
                        'response': response.content.decode(),
                        'response_data': decrypted_response,
                        'verified': verified,
                        'date_respond': fields.Datetime.now(),
                        'state': 'done',
                    })
                except Exception as e:
                    status_log.write({
                        'name': "Failed On" + str(fields.Datetime.now()),
                        'state': 'fail',
                        'failure_stack': traceback.format_exc(),
                        'response': str(e),
                    })
        self.env.cr.commit()
        self.env['hsbc.api.log'].search([], limit=1).process_pay_status()
