# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, registry, SUPERUSER_ID
from odoo.tools.misc import formatLang, format_date, get_lang, clean_context, split_every, xlsxwriter
from odoo.tools.translate import _
from odoo.tools import append_content_to_html, DEFAULT_SERVER_DATE_FORMAT, html2plaintext
from odoo.exceptions import UserError
import threading
import logging
import io
from datetime import datetime, date
import base64

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    from_omt = fields.Boolean('From OMT')
    omt_inv_number = fields.Char('OMT Invoice Number')

    @api.model
    def create(self, vals_list):
        if vals_list.get('omt_inv_number'):
            vals_list.update({'from_omt': 1})
        return super(AccountMove, self).create(vals_list)

    @api.onchange('invoice_date')
    def _onchange_invoice_date(self):
        if self.invoice_date:
            if not self.invoice_payment_term_id:
                self.invoice_date_due = self.invoice_date
            self._get_lines_onchange_currency()


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    program = fields.Char(string="Program ID", store=True)
    points = fields.Char(store=True)


class Partner(models.Model):
    _inherit = "res.partner"

    cc_email = fields.Char(string="CC")
    email = fields.Char(string="To")
    followup_report_level = fields.Selection([
        ('customer', 'Customer Level'),
        ('entity', 'Entity/Tag Level'),
    ], default='customer')

    def default_bank_domain(self):
        company = self.env['res.company'].search([], limit=1)
        return [('partner_id', '=', company.partner_id.id)]

    invoice_partner_bank_id = fields.Many2one('res.partner.bank', string="Recipient Bank", domain=default_bank_domain)

    @api.depends('is_company', 'name', 'parent_id.name', 'type', 'company_name')
    @api.depends_context('show_address', 'show_address_only', 'show_email', 'html_format', 'show_vat')
    def _compute_display_name(self):
        diff = dict(show_address=None, show_address_only=None, show_email=None, html_format=None, show_vat=None)
        names = dict(self.with_context(**diff).name_get())
        for partner in self:
            if partner.ref:
                partner.display_name = names.get(partner.id) + ' - ' + partner.ref
            else:
                partner.display_name = names.get(partner.id)


class DimensionField(models.Model):
    _inherit = "account.cost.center"

    account_id = fields.Many2one("account.account", string="Account")


class AccountFollowupReport(models.AbstractModel):
    _inherit = "account.followup.report"

    def _get_columns_name(self, options):
        """
        Override
        Return the name of the columns of the follow-ups report
        """
        headers = [
                   {'name': _('Invoice Number'), 'class': 'date', 'style': 'text-align:center; white-space:nowrap;'},
                   {'name': _('OMT Invoice Number'), 'class': 'date', 'style': 'text-align:center; white-space:nowrap;'},
                   {'name': _('Date'), 'class': 'date', 'style': 'text-align:center; white-space:nowrap;'},
                   {'name': _('Due Date'), 'class': 'date', 'style': 'text-align:center; white-space:nowrap;'},
                   {'name': _('Source Document'), 'style': 'text-align:center; white-space:nowrap;display:none;'},
                   {'name': _('Description'), 'style': 'text-align:center; white-space:nowrap;'},
                   {'name': _('Expected Date'), 'class': 'date', 'style': 'white-space:nowrap;'},
                   {'name': _('Excluded'), 'class': 'date', 'style': 'white-space:nowrap;'},
                   {'name': _('Total Due'), 'class': 'number o_price_total', 'style': 'text-align:right; '
                                                                                      'white-space:nowrap;'}
                  ]
        headers_1 = [{'name': _('PO Number'), 'class': 'date', 'style': 'text-align:center; white-space:nowrap;'},]
        if self.env.context.get('print_mode'):
            headers = headers[:1] + headers_1[:1] + headers[2:6] + headers[8:]
            # Remove the 'OMT Invoice Number', 'Expected Date' and 'Excluded' columns
        return headers

    def _get_lines(self, options, line_id=None, print_mode=False):
        """
        Override
        Compute and return the lines of the columns of the follow-ups report.
        """
        # Get date format for the lang
        partner = options.get('partner_id') and self.env['res.partner'].browse(options['partner_id']) or False
        if not partner:
            return []

        lang_code = partner.lang if self._context.get('print_mode') else self.env.user.lang or get_lang(self.env).code
        lines = []
        res = {}
        today = fields.Date.today()
        line_num = 0
        if partner.followup_report_level == 'entity':
            partners_list = self.env['res.partner'].search([('category_id', '=', partner.category_id.id)])
            # print(partners_list)
            unreconciled = partners_list.mapped('unreconciled_aml_ids')
            # print('entity')
        else:
            unreconciled = partner.unreconciled_aml_ids
        # print(unreconciled)
        # for l in partner.unreconciled_aml_ids.filtered(lambda l: l.company_id == self.env.company):
        for l in unreconciled.filtered(lambda l: l.company_id == self.env.company):
            if l.company_id == self.env.company:
                if self.env.context.get('print_mode') and l.blocked:
                    continue
                currency = l.currency_id or l.company_id.currency_id
                if currency not in res:
                    res[currency] = []
                res[currency].append(l)
        for currency, aml_recs in res.items():
            total = 0
            total_issued = 0

            for aml in aml_recs:
                amount = aml.amount_residual_currency if aml.currency_id else aml.amount_residual
                date_due = format_date(self.env, aml.date_maturity or aml.date, lang_code=lang_code)
                total += not aml.blocked and amount or 0
                is_overdue = today > aml.date_maturity if aml.date_maturity else today > aml.date
                is_payment = aml.payment_id
                purchase_number = aml.move_id.purchase_id.name
                if is_overdue or is_payment:
                    total_issued += not aml.blocked and amount or 0
                if is_overdue:
                    date_due = {'name': date_due, 'class': 'color-red date', 'style': 'white-space:nowrap;text-align:center;color: red;'}
                if is_payment:
                    date_due = ''
                # move_line_name = aml.move_id.ref
                move_line_name = aml.move_id.invoice_line_ids[0].name
                if self.env.context.get('print_mode'):
                    move_line_name = {'name': move_line_name, 'style': 'text-align:left; white-space:normal;'}
                amount = formatLang(self.env, amount, currency_obj=currency)
                line_num += 1
                expected_pay_date = format_date(self.env, aml.expected_pay_date, lang_code=lang_code) if aml.expected_pay_date else ''
                invoice_origin = aml.move_id.invoice_origin or ''
                if len(invoice_origin) > 43:
                    invoice_origin = invoice_origin[:40] + '...'
                omt_number = ''
                if aml.move_id.from_omt:
                    omt_number = aml.move_id.omt_inv_number
                columns = [
                    omt_number,
                    format_date(self.env, aml.date, lang_code=lang_code),
                    date_due,
                    invoice_origin,
                    move_line_name,
                    (expected_pay_date and expected_pay_date + ' ') + (aml.internal_note or ''),
                    {'name': '', 'blocked': aml.blocked},
                    amount,
                ]
                columns_1 = [
                    purchase_number,
                ]
                if self.env.context.get('print_mode') or print_mode:
                    columns = columns_1 + columns[1:5] + columns[7:]
                inv_number = aml.move_id.name
                if self.env.context.get('print_mode') or print_mode and aml.move_id.from_omt:
                    if len(omt_number.strip()) > 3:
                        inv_number = omt_number
                lines.append({
                    'id': aml.id,
                    'account_move': aml.move_id,
                    'name': inv_number,
                    'caret_options': 'followup',
                    'move_id': aml.move_id.id,
                    'type': is_payment and 'payment' or 'unreconciled_aml',
                    'unfoldable': False,
                    'columns': [type(v) == dict and v or {'name': v} for v in columns],
                    'blocked': aml.blocked,
                })
            total_due = formatLang(self.env, total, currency_obj=currency)
            line_num += 1
            lines.append({
                'id': line_num,
                'name': '',
                'class': 'total',
                'style': 'border-top-style: double',
                'unfoldable': False,
                'level': 3,
                'columns': [{'name': v} for v in [''] * (4 if self.env.context.get('print_mode') or print_mode else 6) + [total >= 0 and _('Total Due') or '', total_due]],
            })
            # print(lines)
            if total_issued > 0:
                total_issued = formatLang(self.env, total_issued, currency_obj=currency)
                line_num += 1
                lines.append({
                    'id': line_num,
                    'name': '',
                    'class': 'total',
                    'unfoldable': False,
                    'level': 3,
                    'columns': [{'name': v} for v in [''] * (4 if self.env.context.get('print_mode') or print_mode else 6) + [_('Total Overdue'), total_issued]],
                })
            # Add an empty line after the total to make a space between two currencies
            line_num += 1
            lines.append({
                'id': line_num,
                'name': '',
                'class': '',
                'style': 'border-bottom-style: none',
                'unfoldable': False,
                'level': 0,
                'columns': [{} for col in columns],
            })
        # Remove the last empty line
        if lines:
            lines.pop()
        # print(lines)
        return lines

    @api.model
    def send_email(self, options):
        """
        Send by mail the followup to the customer
        """
        partner = self.env['res.partner'].browse(options.get('partner_id'))
        non_blocked_amls = partner.unreconciled_aml_ids.filtered(lambda aml: not aml.blocked)
        if not non_blocked_amls:
            return True
        non_printed_invoices = partner.unpaid_invoices.filtered(lambda inv: not inv.message_main_attachment_id)
        if non_printed_invoices and partner.followup_level.join_invoices:
            raise UserError(
                _('You are trying to send a followup report to a partner for which you didn\'t print all the invoices ({})').format(
                    " ".join(non_printed_invoices.mapped('name'))))
        invoice_partner = self.env['res.partner'].browse(partner.address_get(['invoice'])['invoice'])
        email = invoice_partner.email
        options['keep_summary'] = True
        if email and email.strip():
            self = self.with_context(lang=partner.lang or self.env.user.lang)
            # When printing we need te replace the \n of the summary by <br /> tags
            body_html = self.with_context(print_mode=True, mail=True).get_html(options)
            body_html = body_html.replace(b'o_account_reports_edit_summary_pencil',
                                          b'o_account_reports_edit_summary_pencil d-none')
            start_index = body_html.find(b'<span>', body_html.find(b'<div class="o_account_reports_summary">'))
            end_index = start_index > -1 and body_html.find(b'</span>', start_index) or -1
            if end_index > -1:
                replaced_msg = body_html[start_index:end_index].replace(b'\n', b'')
                body_html = body_html[:start_index] + replaced_msg + body_html[end_index:]
            body_html = body_html.replace(b'<div class="print_only"><h2>Followup Report</h2></div>',
                                          b'<div class="print_only"><h2>Outstanding Invoices</h2></div>')
            attachments_list = []
            lines_unblocked = list(filter(lambda line: not line.get('blocked'), self._get_lines(options)))
            if len(lines_unblocked) > 7:
                file_name = f'Outstanding details.xlsx'
#                 self.env['ir.attachment'].search([('name', '=', file_name)]).unlink()
                attachment = self.env['ir.attachment'].create({
                    'name': file_name,
                    'datas': self.get_xlsx(options),
                })
                attachments_list = [attachment.id]
            if partner.followup_level.join_invoices:
                attachments_list += partner.unpaid_invoices.message_main_attachment_id.ids

            partner.with_context(mail_post_autofollow=True, lang=partner.lang or self.env.user.lang).message_post(
                partner_ids=[invoice_partner.id],
                body=body_html,
                subject=_('BIW – Outstanding Invoices') + ' - ' + partner.name,
                subtype_id=self.env.ref('mail.mt_note').id,
                model_description=_('Outstanding Invoices'),
                email_layout_xmlid='bi_custom_accounting.mail_notification_light_inherited',
                attachment_ids=attachments_list,
                record_name=partner.name
            )
            return True
        raise UserError(
            _('Could not send mail to partner %s because it does not have any email address defined') % partner.display_name)

    def get_xlsx(self, options, response=None):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'strings_to_formulas': False,
        })
        sheet = workbook.add_worksheet(self._get_report_name())
        sheet.set_column('G:G', 25)
        default_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2})
        default_col1_style.set_align('center')
        default_col1_style.set_align('vcenter')
        default_style = workbook.add_format({'text_wrap': True, 'font_name': 'Arial', 'font_size': 10})
        default_style.set_align('center')
        default_style.set_align('vcenter')
        default_style_1 = workbook.add_format({'text_wrap': True, 'font_name': 'Arial', 'font_size': 10, 'align': 'right'})
        default_style_1.set_align('center')
        default_style_1.set_align('vcenter')
        right_style = workbook.add_format({'text_wrap': True, 'font_name': 'Arial', 'font_size': 10})
        right_style.set_align('right')
        right_style.set_align('vcenter')
        format_3 = workbook.add_format({'num_format': 'dd-mm-yyyy', 'text_wrap': True, 'font_name': 'Arial', 'font_size': 10})
        format_3.set_align('center')
        format_3.set_align('vcenter')

        lines_all = self._get_lines(options, print_mode=True)
        lines = []
        for i in range(len(lines_all)):
            if not lines_all[i].get('blocked'): #and lines_all[i].get('account.move'):
                lines.append(lines_all[i])
        lines_len = len(lines)
        header_cols = self._get_columns_name(options)
        header_cols= header_cols[:1] + header_cols[2:4] + header_cols[5:6] + header_cols[8:]
        head_len = len(header_cols)
        sheet.set_column(0, head_len, 25)
        for i in range(1, head_len+1):
            if i == 1:
               sheet.write(0, i, header_cols[i-1]['name'], default_col1_style)
            else:
               sheet.write(0, i+1, header_cols[i-1]['name'], default_col1_style)
        for j in range(lines_len):
            sheet.set_row(j+1, 50)
            sheet.write(j+1, 1, lines[j].get('name'), default_style)
            for i in range(1, head_len):
                if i < 3:
                    sheet.write(j+1, i+4, lines[j].get('columns')[i-3].get('name') or '-', right_style)
                elif i > 3:
                    sheet.write(j+1, 3, lines[j].get('columns')[i-3].get('name') or '-', default_style)

            sheet.write(j+1, 4, lines[j].get('columns')[i-2].get('name') or '-', default_style)
        sheet.write(0, 0, 'Customer', default_col1_style)
        sheet.write(0, 2, 'PO Number', default_col1_style)
        for i in range(1, lines_len-1):
            if lines[i-1].get('account_move'):
                sheet.write(i, 0, lines[i-1].get('account_move').partner_id.name or '-', default_style)
                sheet.write(i, 2, lines[i-1].get('account_move').purchase_id.name or '-', default_style)

        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()
        # raise UserError('Wait...')
        return base64.encodebytes(generated_file)


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _notify_record_by_email(self, message, recipients_data, msg_vals=False,
                                model_description=False, mail_auto_delete=True, check_existing=False,
                                force_send=True, send_after_commit=True,
                                **kwargs):
        """ Method to send email linked to notified messages.

        :param message: mail.message record to notify;
        :param recipients_data: see ``_notify_thread``;
        :param msg_vals: see ``_notify_thread``;

        :param model_description: model description used in email notification process
          (computed if not given);
        :param mail_auto_delete: delete notification emails once sent;
        :param check_existing: check for existing notifications to update based on
          mailed recipient, otherwise create new notifications;

        :param force_send: send emails directly instead of using queue;
        :param send_after_commit: if force_send, tells whether to send emails after
          the transaction has been committed using a post-commit hook;
        """
        partners_data = [r for r in recipients_data['partners'] if r['notif'] == 'email']
        if not partners_data:
            return True

        model = msg_vals.get('model') if msg_vals else message.model
        model_name = model_description or (self.with_lang().env['ir.model']._get(model).display_name if model else False) # one query for display name
        recipients_groups_data = self._notify_classify_recipients(partners_data, model_name, msg_vals=msg_vals)

        if not recipients_groups_data:
            return True
        force_send = self.env.context.get('mail_notify_force_send', force_send)

        template_values = self._notify_prepare_template_context(message, msg_vals, model_description=model_description) # 10 queries

        email_layout_xmlid = msg_vals.get('email_layout_xmlid') if msg_vals else message.email_layout_xmlid
        template_xmlid = email_layout_xmlid if email_layout_xmlid else 'mail.message_notification_email'
        try:
            base_template = self.env.ref(template_xmlid, raise_if_not_found=True).with_context(lang=template_values['lang']) # 1 query
        except ValueError:
            _logger.warning('QWeb template %s not found when sending notification emails. Sending without layouting.' % (template_xmlid))
            base_template = False

        mail_subject = message.subject or (message.record_name and 'Re: %s' % message.record_name) # in cache, no queries
        # Replace new lines by spaces to conform to email headers requirements
        mail_subject = ' '.join((mail_subject or '').splitlines())
        # prepare notification mail values
        base_mail_values = {
            'mail_message_id': message.id,
            'mail_server_id': message.mail_server_id.id, # 2 query, check acces + read, may be useless, Falsy, when will it be used?
            'auto_delete': mail_auto_delete,
            # due to ir.rule, user have no right to access parent message if message is not published
            'references': message.parent_id.sudo().message_id if message.parent_id else False,
            'subject': mail_subject,
        }
        base_mail_values = self._notify_by_email_add_values(base_mail_values)

        # Clean the context to get rid of residual default_* keys that could cause issues during
        # the mail.mail creation.
        # Example: 'default_state' would refer to the default state of a previously created record
        # from another model that in turns triggers an assignation notification that ends up here.
        # This will lead to a traceback when trying to create a mail.mail with this state value that
        # doesn't exist.
        SafeMail = self.env['mail.mail'].sudo().with_context(clean_context(self._context))
        SafeNotification = self.env['mail.notification'].sudo().with_context(clean_context(self._context))
        emails = self.env['mail.mail'].sudo()

        # loop on groups (customer, portal, user,  ... + model specific like group_sale_salesman)
        notif_create_values = []
        recipients_max = 50
        for recipients_group_data in recipients_groups_data:
            # generate notification email content
            recipients_ids = recipients_group_data.pop('recipients')
            render_values = {**template_values, **recipients_group_data}
            # {company, is_discussion, lang, message, model_description, record, record_name, signature, subtype, tracking_values, website_url}
            # {actions, button_access, has_button_access, recipients}

            if base_template:
                mail_body = base_template.render(render_values, engine='ir.qweb', minimal_qcontext=True)
            else:
                mail_body = message.body
            mail_body = self._replace_local_links(mail_body)

            # create email
            for recipients_ids_chunk in split_every(recipients_max, recipients_ids):
                recipient_values = self._notify_email_recipient_values(recipients_ids_chunk)
                email_to = recipient_values['email_to']
                recipient_ids = recipient_values['recipient_ids']

                p = self.env['res.partner'].browse(recipient_ids)

                create_values = {
                    'body_html': mail_body,
                    'subject': mail_subject,
                    'recipient_ids': [(4, pid) for pid in recipient_ids],
                }

                if p:
                    for cc in p:
                        email_cc = cc.cc_email
                        create_values['email_cc'] = email_cc

                if email_to:
                    create_values['email_to'] = email_to
                create_values.update(base_mail_values)  # mail_message_id, mail_server_id, auto_delete, references, headers
                email = SafeMail.create(create_values)

                if email and recipient_ids:
                    tocreate_recipient_ids = list(recipient_ids)
                    if check_existing:
                        existing_notifications = self.env['mail.notification'].sudo().search([
                            ('mail_message_id', '=', message.id),
                            ('notification_type', '=', 'email'),
                            ('res_partner_id', 'in', tocreate_recipient_ids)
                        ])
                        if existing_notifications:
                            tocreate_recipient_ids = [rid for rid in recipient_ids if rid not in existing_notifications.mapped('res_partner_id.id')]
                            existing_notifications.write({
                                'notification_status': 'ready',
                                'mail_id': email.id,
                            })
                    notif_create_values += [{
                        'mail_message_id': message.id,
                        'res_partner_id': recipient_id,
                        'notification_type': 'email',
                        'mail_id': email.id,
                        'is_read': True,  # discard Inbox notification
                        'notification_status': 'ready',
                    } for recipient_id in tocreate_recipient_ids]
                emails |= email

        if notif_create_values:
            SafeNotification.create(notif_create_values)

        # NOTE:
        #   1. for more than 50 followers, use the queue system
        #   2. do not send emails immediately if the registry is not loaded,
        #      to prevent sending email during a simple update of the database
        #      using the command-line.
        test_mode = getattr(threading.currentThread(), 'testing', False)
        if force_send and len(emails) < recipients_max and (not self.pool._init or test_mode):
            # unless asked specifically, send emails after the transaction to
            # avoid side effects due to emails being sent while the transaction fails
            if not test_mode and send_after_commit:
                email_ids = emails.ids
                dbname = self.env.cr.dbname
                _context = self._context
                def send_notifications():
                    db_registry = registry(dbname)
                    with api.Environment.manage(), db_registry.cursor() as cr:
                        env = api.Environment(cr, SUPERUSER_ID, _context)
                        env['mail.mail'].browse(email_ids).send()
                self._cr.after('commit', send_notifications)
            else:
                emails.send()

        return True
