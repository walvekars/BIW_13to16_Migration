from odoo import models, fields, api, _
from . import hsbc_api
from odoo.exceptions import ValidationError, UserError


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.payment'

    mode_of_payment = fields.Selection([
        ('cash', 'Cash'),
        ('bank', 'Bank')], string='Mode of Payment')
    hsbc_payment = fields.Boolean('Is HSBC Payment')
    hsbc_status = fields.Selection([
        ('not_initiated', 'Not Initiated'),
        ('initiated', 'In Process'),
        ('sent', 'Payment Data Sent - Awaiting Approval'),
        # ('fail', 'Failed to send payment'),
        ('approved', 'Payment Approved & Posted'),
        ('rejected', 'Payment Rejected'),
    ], string="HSBC Payment Status", readonly=True, default="not_initiated", tracking=True)
    utr_ref = fields.Char('UTR')
    hsbc_trigger = fields.Boolean()
    approval_status = fields.Selection([('approved', 'Approved'),
                                        ('pending', 'Pending')], readonly=True)
    # partner_id_bank = fields.Many2one('res.partner.bank', string="Vendor Bank Account")
    

    @api.onchange('partner_id')
    def vendor_acc_det(self):
        account_payment = self.env['res.partner'].search([('id', '=', self.partner_id.id)])
        self.partner_bank_id = account_payment.bank_ids
#testing3

    def initiate_hsbc_payment(self):
        print("Inside func")
        for i in self:
            if i.state == 'sent':
                raise ValidationError(f'HSBC payment already initiated')
        print("After 2nd loop")
        for rec in self.filtered(lambda payment:
                                 payment.mode_of_payment == 'bank'
                                 and payment.hsbc_status == 'not_initiated'
                                 and payment.state == 'draft'):
            print("after 2nd loop")
            if rec.payment_type != 'outbound':
                raise ValidationError(
                    f'HSBC payment can be initiated for outbound payments only! Ref:({rec.id}/{rec.name})')
            print('after 1st validation')
            if not rec.journal_id.name == 'HSBC INR Account' or not rec.journal_id.code == 'BNK13' or not rec.journal_id.type == 'bank':
                raise ValidationError(
                    f'You cannot initiate HSBC payment for {rec.journal_id.name}')
            print("after 2nd validation")
            if not rec.partner_id:
                raise ValidationError(f'Cannot Initiate HSBC Payment without a vendor! Ref:({rec.id}/{rec.name})')
            print("after 3rd validation")
            if not rec.partner_bank_id:
                raise ValidationError(f'Please configure bank account for vendor. Ref:({rec.name})')
            print("after 4th validation")

            self.env['hsbc.account.payment'].create({
                'account_payment': rec.id,
                'amount': float(rec.amount),
                'hsbc_users': self.env.uid,
                'create_time': fields.datetime.now(),
                'state': 'request_pending',
            })
            print("after record creation")
            rec.hsbc_status = 'initiated'
            rec.state = 'posted'
            print("records created")

    def re_initiate_rejected(self):
        for rec in self.filtered(lambda pay: pay.hsbc_status == 'rejected'):
            self.env['hsbc.account.payment'].create({
                'account_payment': rec.id,
                'amount': float(rec.amount),
                'hsbc_users': self.env.uid,
                'create_time': fields.datetime.now(),
                'state': 'request_pending',
            })
            rec.hsbc_status = 'initiated'
