from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, _
from datetime import timedelta
from num2words import num2words
import pdb


class Contacts(models.Model):
    _name = 'res.purchase.order'

    name = fields.Char(string="Purchase Ref")
    purchase_value_po = fields.Monetary(string="Purchase Value")
    purchase_validity_po = fields.Date(string="Purchase Validity")
    attach_po = fields.Binary(string="Attachments")
#     res_partner_po = fields.Many2one('res.partner')
    partner_id = fields.Many2one('res.partner')
    currency_id = fields.Many2one('res.currency')
    purchase_value_remains = fields.Monetary(string="Remaining Amount", compute="compute_purchase_value_remain")
    purchase_value_utilized = fields.Monetary(string="Utilized Amount", compute="compute_purchase_value_remain")
    utilized_amount_percentage = fields.Float(string="Utilized %", compute="compute_purchase_value_remain")

    @api.onchange('name')
    def onchange_name_po(self):
        if self.name:
            error = self.env['res.purchase.order'].search_count([('name', '=', self.name)])
            if error:
                raise UserError("This reference is already used on another purchase order...!!")

    def compute_purchase_value_remain(self):
        for rec in self:
            invoices = rec.env['account.move'].search([('res_purchase_id', '=', rec.id), ('type', '=', 'out_invoice')])
            invoices_sum = 0.0
            for inv in invoices:
                invoices_sum += inv.amount_untaxed

            credit_invoices = rec.env['account.move'].search(
                [('res_purchase_id', '=', rec.id), ('type', '=', 'out_refund')])
            credit_invoices_sum = 0.0
            # if credit_invoices:
            for credit in credit_invoices:
                credit_invoices_sum += credit.amount_untaxed

            rec.purchase_value_utilized = invoices_sum - credit_invoices_sum
            rec.purchase_value_remains = rec.purchase_value_po - rec.purchase_value_utilized
            try:
                rec.utilized_amount_percentage = rec.purchase_value_utilized / rec.purchase_value_po
            except ZeroDivisionError:
                rec.utilized_amount_percentage = 1
#             if rec.purchase_value_remains < 0:
#                 raise ValidationError(_('The Invoice cannot be raised for amount exceeding the available amount' +
#                                         ' for the purchase ref: ' + rec.name))

    def send_mail_reminders(self):
        today = fields.Date.today()
        cc_receipt_list = ""
        cc_group = self.env.ref('bi_world_purchase_custom.purchase_cc_list')

        for user in cc_group.users:
            cc_receipt_list += user.partner_id.email + ", "
        valid_records = self.env['res.purchase.order'].search([('purchase_validity_po', '>=', today)])
        consumed_records = valid_records.filtered(lambda po: po.utilized_amount_percentage >= 0.7)
        for rec in consumed_records:
            email = self.env['res.email'].search_count([('partner_id', '=', rec.partner_id.id)])
            if email == 0:
                mail_body = f'''Dear Customer, <br/><br/><br/>
                This is a gentle reminder that your Purchase Order (Ref:{rec.name}) of amount
                {rec.purchase_value_po: ,} has been {round(rec.utilized_amount_percentage * 100)}% consumed.<br/><br/>
                Please expedite for a new PO.<br/><br/><br/>
                Regards,<br/>
                {self.env.company.name}
                '''
                mail_values = {
                    'subject': f"{rec.partner_id.name} : Purchase Order {rec.name} has Exceeded 70% Consumption",
                    'body_html': mail_body,
                    'email_to': rec.partner_id.email,
                    'email_cc': cc_receipt_list,
                    # 'email_from': email_from,
                }
                # mail =
                self.env['mail.mail'].create(mail_values).send()

        start_date = today + timedelta(21)
        expiring_records = self.env['res.purchase.order'].search([('purchase_validity_po', '>=', today),
                                                                  ('purchase_validity_po', '<=', start_date)])
        for rec in expiring_records:
            email = self.env['res.email'].search_count([('partner_id', '=', rec.partner_id.id)])
            if email == 0:
                mail_body = f'''Dear Customer, <br/><br/><br/>
                This is a gentle reminder that your Purchase Order (Ref:{rec.name}) of amount
                {rec.purchase_value_po: ,} will expire on {rec.purchase_validity_po}.<br/><br/>
                Please expedite for a new PO.<br/><br/><br/>
                Regards,<br/>
                {self.env.company.name}
                '''
                mail_values = {
                    'subject': f"{rec.partner_id.name} : Purchase Order {rec.name} is nearing Expiration",
                    'body_html': mail_body,
                    'email_to': rec.partner_id.email,
                    'email_cc': cc_receipt_list,
                    # 'email_from': email_from,
                }
                # mail =
                self.env['mail.mail'].create(mail_values).send()


    










