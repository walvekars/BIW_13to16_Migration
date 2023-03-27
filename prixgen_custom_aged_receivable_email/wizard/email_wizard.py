# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class SendmailWizard(models.TransientModel):
    _name = 'send.mail.wizard'
    _description = 'Send email Custom Wizard'


    partner_ids = fields.Many2many(
        'res.partner', 'send_mail_wizard_res_partner_rel',
        'wizard_id', 'partner_id', 'Additional Contacts')
    cc_ids = fields.Many2many('res.partner', string="Cc")
    subject = fields.Char(string="Subject", required=True)
    body = fields.Html(string="Body")
    attachment_ids = fields.Many2many('ir.attachment', string="Attachment")

    # template_id = fields.Many2one('mail.template', string="Use Template")
    # email_from = fields.Char('From',
    #                          help="Email address of the sender. This field is set when no matching partner is found and replaces the author_id field in the chatter.")

    def action_send_mail(self):
        template_obj = self.env['mail.template'].sudo().search([('name', '=', 'Email Template Name')], limit=1)
        receipt_list = []
        email_cc = []
        if not template_obj:
            if self.partner_ids:
                for partner in self.partner_ids:
                    if partner.email:
                        receipt_list.append(partner.email)
                    else:
                        pass
            if self.cc_ids:
                for cc in self.cc_ids:
                    if cc.email:
                        email_cc.append(cc.email)
                    else:
                        pass

            current_user = self.env.user
            email_from = current_user.partner_id.email
            from_name = current_user.partner_id.name
            mail_servers = self.env['ir.mail_server'].sudo().search([], order='sequence')
            if mail_servers:
                email_from = f"\"{from_name}\" <{mail_servers[0].smtp_user}>"

            body = template_obj.body_html
            body = self.body

            mail_values = {
                'subject': self.subject,
                'body_html': body,
                'email_to': ','.join(map(lambda x: x, receipt_list)),
                'email_cc': ','.join(map(lambda x: x, email_cc)),
                'email_from': email_from,
                'attachment_ids': [(6, 0, self.attachment_ids.ids)]
            }
            create_and_send_email = self.env['mail.mail'].create(mail_values).send()
