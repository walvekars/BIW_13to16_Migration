from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta


class InheritAccountReport(models.AbstractModel):
    _inherit = 'account.report'

    def print_pdf(self, options):
        return {
            'type': 'ir_actions_account_report_download',
            'data': {'model': self.env.context.get('model'),
                     'options': json.dumps(options),
                     'output_format': 'pdf',
                     'financial_id': self.env.context.get('id'),
                     }
        }

    def custom_send_mail(self, options):
#         print("Custom Send Mail-----------------------------------------", options)
        new_wizard = self.env['account_reports.export.wizard'].create(
            {'report_model': self._name, 'report_id': self.id})
        new_wizard.write({'export_format_ids': [(6, 0, [self.env['account_reports.export.wizard.format'].search(
            [('export_wizard_id', '=', new_wizard.id), ('name', '=', 'PDF')]).id])],
                          'doc_name': 'Aged_receivable'})
        new_wizard.env.context = dict(new_wizard.env.context)
        # print(options,new_wizard,"@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
        new_wizard.env.context.update({'account_report_generation_options': options})
        # attachment_ids = new_wizard.export_report_custom()

        base_url = self.env['ir.config_parameter'].sudo().get_param('report.url') or self.env[
            'ir.config_parameter'].sudo().get_param('web.base.url')

        # Prevent inconsistency between options and context.
        self = self.with_context(self._set_context(options))
        lines = self._get_lines(options, line_id=None)
        if options.get('hierarchy'):
            lines = self._create_hierarchy(lines, options)
        if options.get('selected_column'):
            lines = self._sort_lines(lines, options)
        # print(lines, "\n\n")
        i = 0
        while i < (len(lines) - 1):
            if lines[i]['columns'][3]['name'] != '':
                lines.pop(i)
                i -= 1
            i += 1

        i = 0
        while i < (len(lines) - 2):
            _i = self.env['res.partner'].browse(lines[i]['partner_id']).category_id
            if _i:
                j = i + 1
                while j < (len(lines) - 1):
                    _i1 = self.env['res.partner'].browse(lines[j]['partner_id']).category_id
                    # print(_i, _i1)
                    if _i1:
                        if _i[0] == _i1[0]:
                            for k in range(6, 14):
                                lines[i]['columns'][k]['no_format'] += lines[j]['columns'][k]['no_format']
                            # lines[i]['last_week_amt'] += lines[j]['last_week_amt']
                            lines.pop(j)
                            j -= 1
                    j += 1
            i += 1
        # print(lines, "Lines End=======================================")
        payments = self.env['account.payment'].search([('payment_date', '>',
                                                        datetime.strptime(options['date']['date_to'], '%Y-%m-%d')
                                                        - relativedelta(days=8)),
                                                       ('payment_date', '<=',
                                                        datetime.strptime(options['date']['date_to'], '%Y-%m-%d')),
                                                       ('payment_type', '=', 'inbound'),
                                                       ('partner_type', '=', 'customer'),
                                                       ('state', 'not in', ['draft', 'cancelled'])])

        tot_week_amt = 0
        week_aging_365 = 0
        week_aging_180 = 0
        week_aging_90 = 0
        n = len(lines)
        for j in range(n):
            # print(lines[j])
            lines[j].update({'tag_amt': 0, 'week_90': 0, 'week_180': 0, 'week_365': 0})
            # lines[j].update({'tag_amt': tot_week_amt})
            aging_365 = 0
            aging_180 = 0
            aging_90 = 0
            tot_amt = 0
            partner = lines[j].get('partner_id') and self.env['res.partner'].browse(lines[j]['partner_id'])
            if partner and partner.category_id:
                tag_id = partner.category_id
                for payment in payments:
                    if payment.partner_id.category_id == tag_id:
                        # if not lines[j]['last_week_amt']:
                        #     print('HI HELLO', payment.name, payment.partner_id.name, payment.amount)
                        tot_amt += payment.amount
                        r_inv = payment.reconciled_invoice_ids
                        # print(payment.name, r_inv)
                        if len(r_inv) == 1:
                            # print(r_inv[0].name, r_inv[0].amount_total, r_inv[0].invoice_date_due, r_inv[0].amount_residual)
                            # print(payment.payment_date, r_inv[0].invoice_date_due, (payment.payment_date - r_inv[0].invoice_date_due).days)
                            aging = (payment.payment_date - r_inv[0].invoice_date_due).days
                            if aging >= 365:
                                aging_365 += payment.amount
                            elif aging >= 180:
                                aging_180 += payment.amount
                            elif aging >= 90:
                                aging_90 += payment.amount

                tot_week_amt += tot_amt
                week_aging_365 += aging_365
                week_aging_180 += aging_180
                week_aging_90 += aging_90
                lines[j].update({'tag_amt': tot_amt, 'week_90': aging_90, 'week_180': aging_180, 'week_365': aging_365})
#                 print(lines[j])

        lines[-1].update({'tag_amt': tot_week_amt, 'week_90': week_aging_90, 'week_180': week_aging_180, 'week_365': week_aging_365})
#         print(lines[-1])

            # prev, new = lines[j]['last_week_amt'], lines[j]['tag_amt']
            # print(prev == new, prev, new, partner.name)

        report_manager = self._get_report_manager(options)
        report = {'name': self._get_report_name(),
                  'summary': report_manager.summary,
                  'company_name': self.env.company.name, }

        rcontext = {
            'mode': 'print',
            'base_url': base_url,
            'company': self.env.company,
            'lines': lines,
            'self': self,
            'options': options,
            'report': report,
        }

        body = self.env['ir.ui.view'].render_template(
            # "account_reports.print_template",
            "prixgen_custom_aged_receivable_email.aged_receivable_email_template",
            values=dict(rcontext),
        )
        # body_html = self.with_context(print_mode=True).get_html(options)
        # body = body.replace(b'<body class="o_account_reports_body_print">',
        #                     b'<body class="o_account_reports_body_print">' + body_html)
        # body = body.replace(b"Partner Tag", b"")
        # body = body.replace(b"Analytic Account", b"")
        # body = body.replace(b"Due Date", b"")
        # body = body.replace(b"Journal", b"")
        # body = body.replace(b"Account", b"")
        # body = body.replace(b"Exp. Date", b"")
        # print(body, "BODY:::::::::::::::::::::::::::::::::::::::::::::;\n", body_html)
        lang = self.env.context.get('lang')
        ctx = {'default_partner_ids': [(6, 0, [self.env.user.partner_id.id])], 'default_body': body}
        # 'default_attachment_ids':[(6,0,attachment_ids)],'default_body':body}
        send_mail = {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'send.mail.wizard',
            'views': [(False, 'form')],
            'view_id': self.env.ref('prixgen_custom_aged_receivable_email.send_mail_custom_wizard_form').id,
            'target': 'new',
            'context': ctx,
        }
        return send_mail

        # new_wizard = self.env['account_reports.export.wizard'].create({'report_model': self._name,'report_id': self.id})
        # new_wizard.write({'export_format_ids':[(6,0,[self.env['account_reports.export.wizard.format'].search([('export_wizard_id','=',new_wizard.id),('name','=','PDF')]).id])],
        #                   'doc_name':'Aged_receivable'})
        # new_wizard.env.context = dict(new_wizard.env.context)
        # new_wizard.env.context.update({'account_report_generation_options': options})
        # attachment_ids = new_wizard.export_report_custom()
        # lang = self.env.context.get('lang')
        # ctx = {'default_partner_ids':[(6,0,[self.env.user.partner_id.id])],
        #        'default_attachment_ids':[(6,0,attachment_ids)]}
        # return {
        #     'type': 'ir.actions.act_window',
        #     'view_mode': 'form',
        #     'res_model': 'mail.compose.message',
        #     'views': [(False, 'form')],
        #     'view_id': False,
        #     'target': 'new',
        #     'context': ctx,
        # }


class ReportExportWizard(models.TransientModel):
    """ Wizard allowing to export an accounting report in several different formats
    at once, saving them as attachments.
    """
    _inherit = 'account_reports.export.wizard'

    def export_report_custom(self):
        self.ensure_one()
        created_attachments = self.env['ir.attachment']
        for vals in self._get_attachments_to_save():
            created_attachments |= self.env['ir.attachment'].create(vals)
        return created_attachments.ids


class AccountMove(models.Model):
    _inherit = 'account.move'

    line_ids = fields.One2many('account.move.line', 'move_id', string='Journal Items', copy=True, readonly=False)
                               # ,groups="prixgen_custom_aged_receivable_email.group_analytic_account_hari")
        
    
    def set_access_for_product(self):
        self.able_to_modify_product = self.env['res.users'].has_group('prixgen_custom_aged_receivable_email.group_analytic_account_hari')

    able_to_modify_product = fields.Boolean(compute=set_access_for_product, string='Is user able to modify Journals?')

    def update_journal_analytic(self):
        rec = self.env['account.move'].search([('state', '=', 'posted'), ('type', '=', 'out_invoice')])
        for s in rec:
            lines = s.line_ids.filtered(lambda x: not x.analytic_account_id)
            if s.invoice_line_ids:
                for l in s.invoice_line_ids:
                    if l.analytic_account_id:
                        for line in lines:
                            line.analytic_account_id = l.analytic_account_id
                        break

    def action_post(self):
        post = super(AccountMove, self).action_post()
        if self.partner_id.contact_analytic_account_id:
            self.line_ids.analytic_account_id = self.partner_id.contact_analytic_account_id.id
        return post
    
    @api.onchange('partner_id')
    def add_analytic_accounts(self):
        if self.partner_id.contact_analytic_account_id:
            self.line_ids.analytic_account_id = self.partner_id.contact_analytic_account_id.id
            self.invoice_line_ids.analytic_account_id = self.partner_id.contact_analytic_account_id
    
    def action_post(self):
        rec = self
        for s in rec:
            lines = s.line_ids.filtered(lambda x: not x.analytic_account_id)
            if s.invoice_line_ids:
                for l in s.invoice_line_ids:
                    if l.analytic_account_id:
                        for line in lines:
                            line.analytic_account_id = l.analytic_account_id
                        break
        s = super(AccountMove, self).action_post()
        return s
    

class AccountMoveIn(models.Model):
    _inherit = 'account.move.line'

    def write(self, vals):
        # OVERRIDE
        def field_will_change(line, field_name):
            if field_name not in vals:
                return False
            field = line._fields[field_name]
            if field.type == 'many2one':
                return line[field_name].id != vals[field_name]
            if field.type in ('one2many', 'many2many'):
                current_ids = set(line[field_name].ids)
                after_write_ids = set(r['id'] for r in line.resolve_2many_commands(field_name, vals[field_name], fields=['id']))
                return current_ids != after_write_ids
            if field.type == 'monetary' and line[field.currency_field]:
                return not line[field.currency_field].is_zero(line[field_name] - vals[field_name])
            return line[field_name] != vals[field_name]

        ACCOUNTING_FIELDS = ('debit', 'credit', 'amount_currency')
        BUSINESS_FIELDS = ('price_unit', 'quantity', 'discount', 'tax_ids')
        PROTECTED_FIELDS_TAX_LOCK_DATE = ['debit', 'credit', 'tax_line_id', 'tax_ids', 'tag_ids']
        PROTECTED_FIELDS_LOCK_DATE = PROTECTED_FIELDS_TAX_LOCK_DATE + ['account_id', 'journal_id', 'amount_currency', 'currency_id', 'partner_id']
        PROTECTED_FIELDS_RECONCILIATION = ('account_id', 'date', 'debit', 'credit', 'amount_currency', 'currency_id')

        account_to_write = self.env['account.account'].browse(vals['account_id']) if 'account_id' in vals else None

        # Check writing a deprecated account.
        if account_to_write and account_to_write.deprecated:
            raise UserError(_('You cannot use a deprecated account.'))

        # when making a reconciliation on an existing liquidity journal item, mark the payment as reconciled
        for line in self:
#             if line.parent_state == 'posted':
#                 if line.move_id.restrict_mode_hash_table and set(vals).intersection(INTEGRITY_HASH_LINE_FIELDS):
#                     raise UserError(_("You cannot edit the following fields due to restrict mode being activated on the journal: %s.") % ', '.join(INTEGRITY_HASH_LINE_FIELDS))
#                 if any(key in vals for key in ('tax_ids', 'tax_line_ids')):
#                     if not line.tax_ids:
#                         del vals['tax_ids']
#                 if any(key in vals for key in ('tax_ids', 'tax_line_ids')):
#                     raise UserError(_('You cannot modify the taxes related to a posted journal item, you should reset the journal entry to draft to do so.'))
            if 'statement_line_id' in vals and line.payment_id:
                pay = line.payment_id
                # In case of an internal transfer, there are 2 liquidity move lines to match with a bank statement
                if all(line.statement_id for line in line.payment_id.move_line_ids.filtered(
                        lambda r: r.id != line.id and r.account_id.internal_type == 'liquidity')):
                    pay.state = 'reconciled'
                    # line.payment_id.state = 'reconciled'

            # Check the lock date.
            if any(self.env['account.move']._field_will_change(line, vals, field_name) for field_name in PROTECTED_FIELDS_LOCK_DATE):
                line.move_id._check_fiscalyear_lock_date()

            # Check the tax lock date.
            if any(self.env['account.move']._field_will_change(line, vals, field_name) for field_name in PROTECTED_FIELDS_TAX_LOCK_DATE):
                line._check_tax_lock_date()

            # Check the reconciliation.
            if any(self.env['account.move']._field_will_change(line, vals, field_name) for field_name in PROTECTED_FIELDS_RECONCILIATION):
                line._check_reconciliation()

            # Check switching receivable / payable accounts.
            if account_to_write:
                account_type = line.account_id.account_type
                if line.move_id.is_sale_document(include_receipts=True):
                    if (account_type == 'receivable' and account_to_write.account_type.type != account_type) \
                            or (account_type != 'receivable' and account_to_write.account_type == 'receivable'):
                        raise UserError(_("You can only set an account having the receivable type on payment terms lines for customer invoice."))
                if line.move_id.is_purchase_document(include_receipts=True):
                    if (account_type == 'payable' and account_to_write.account_type.type != account_type) \
                            or (account_type != 'payable' and account_to_write.account_type.type == 'payable'):
                        raise UserError(_("You can only set an account having the payable type on payment terms lines for vendor bill."))

        result = True
        for line in self:
            cleaned_vals = line.move_id._cleanup_write_orm_values(line, vals)
            if not cleaned_vals:
                continue

            result |= super(AccountMoveIn, line).write(cleaned_vals)

            if not line.move_id.is_invoice(include_receipts=True):
                continue

            # Ensure consistency between accounting & business fields.
            # As we can't express such synchronization as computed fields without cycling, we need to do it both
            # in onchange and in create/write. So, if something changed in accounting [resp. business] fields,
            # business [resp. accounting] fields are recomputed.
            if any(field in cleaned_vals for field in ACCOUNTING_FIELDS):
                balance = line.currency_id and line.amount_currency or line.debit - line.credit
                # price_subtotal = line._get_price_total_and_subtotal().get('price_subtotal', 0.0)
                # to_write = line._get_fields_onchange_balance(
                #     balance=balance,
                #     # price_subtotal=price_subtotal,
                # )
                # to_write.update(line._get_price_total_and_subtotal(
                #     price_unit=to_write.get('price_unit', line.price_unit),
                #     quantity=to_write.get('quantity', line.quantity),
                #     discount=to_write.get('discount', line.discount),
                # ))
            #     result |= super(AccountMoveIn, line).write(to_write)
            # elif any(field in cleaned_vals for field in BUSINESS_FIELDS):
            #     # to_write = line._get_price_total_and_subtotal()
            #     # to_write.update(line._get_fields_onchange_subtotal(
            #         price_subtotal=to_write['price_subtotal'],
            #     # ))
            #     result |= super(AccountMoveIn, line).write(to_write)

        # Check total_debit == total_credit in the related moves.
        if self._context.get('check_move_validity', True):
            self.mapped('move_id')._check_balanced(container=True)

        return result

    
    

