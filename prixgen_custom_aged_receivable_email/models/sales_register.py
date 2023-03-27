from odoo import models, api, fields, _
from odoo.tools.misc import format_date, xlsxwriter
import io
from datetime import datetime
import json
# from odoo.tools.misc import xlsxwriter


class SalesRegister(models.Model):
    _name = "sales.register"
    _description = "Sales Register Report"
    _inherit = "account.report"

    filter_date = {'mode': 'range', 'filter': 'this_month'}
    filter_unfold_all = False
    # order_selected_column = {'default': 'Outstanding'}
    # filter_all_entries = {''}

    def _get_columns_name(self, options):
        columns = [
            {'name': _("Sl No"), 'class': '', 'style': 'white-space:nowrap;'},
            {'name': _("Entity Name"), 'class': '', 'style': 'text-align:center; white-space:nowrap;'},
            {'name': _("Status of Company"), 'class': '', 'style': 'text-align:center; white-space:nowrap;'},
            {'name': _("Division"), 'class': '', 'style': 'white-space:nowrap;'},
            {'name': _("Client"), 'class': '', 'style': 'white-space:nowrap;'},
            {'name': _("Billing Type"), 'class': '', 'style': 'white-space:nowrap;'},
            {'name': _("Invoice Description"), 'class': '', 'style': 'white-space:nowrap;'},
            {'name': _("Invoice No"), 'class': '', 'style': 'white-space:nowrap;'},
            {'name': _("Invoice Date"), 'class': 'date', 'style': 'white-space:nowrap;'},
            {'name': _("PO #"), 'class': '', 'style': 'white-space:nowrap;'},
            {'name': _("Program No."), 'class': '', 'style': 'white-space:nowrap;'},
            {'name': _("Currency"), 'class': '', 'style': 'white-space:nowrap;'},
            {'name': _("Points"), 'class': '', 'style': 'white-space:nowrap;'},
            {'name': _("USD Amount"), 'class': '', 'style': 'white-space:nowrap;'},
            {'name': _("Rate"), 'class': '', 'style': 'white-space:nowrap;'},
            {'name': _("Base Amt"), 'class': '', 'style': 'white-space:nowrap;'},
            {'name': _("GST"), 'class': '', 'style': 'white-space:nowrap;'},
            {'name': _("Total Amt"), 'class': '', 'style': 'white-space:nowrap;'},
            {'name': _("Payment"), 'class': '', 'style': 'white-space:nowrap;'},
            {'name': _("Payment Date"), 'class': 'date', 'style': 'white-space:nowrap;'},
            {'name': _("Payment 2"), 'class': '', 'style': 'white-space:nowrap;'},
            {'name': _("Payment Date 2"), 'class': 'date', 'style': 'white-space:nowrap;'},
            {'name': _("TDS"), 'class': '', 'style': 'white-space:nowrap;'},
            {'name': _("Exchange Variation/Bank Charges"), 'class': '', 'style': 'white-space:nowrap;'},
            {'name': _("Outstanding"), 'class': '', 'style': 'white-space:nowrap;'},
            {'name': _("Credit Period of the client"), 'class': '', 'style': 'white-space:nowrap;'},
            {'name': _("Due Date"), 'class': 'date', 'style': 'white-space:nowrap;'},
            {'name': _(datetime.strptime(str(fields.Date.today()), '%Y-%m-%d').strftime('%d-%m-%Y')), 'class': 'date', 'style': 'white-space:nowrap;'},
            {'name': _("Ageing"), 'class': '', 'style': 'white-space:nowrap;'},
            {'name': _("Region"), 'class': '', 'style': 'white-space:nowrap;'},
            # {'name': _("As of: %s") % format_date(self., options['date']['date_to']), 'class': 'number sortable', 'style': 'white-space:nowrap;'},
            # {'name': _("1 - 30"), 'class': 'number sortable', 'style': 'white-space:nowrap;'},
            # {'name': _("31 - 60"), 'class': 'number sortable', 'style': 'white-space:nowrap;'},
            # {'name': _("61 - 90"), 'class': 'number sortable', 'style': 'white-space:nowrap;'},
            # {'name': _("91 - 120"), 'class': 'number sortable', 'style': 'white-space:nowrap;'},
            # {'name': _("Older"), 'class': 'number sortable', 'style': 'white-space:nowrap;'},
            # {'name': _("Total"), 'class': 'number sortable', 'style': 'white-space:nowrap;'},
        ]
        return columns

    @api.model
    def _get_options(self, previous_options=None):

        options = {
            'unfolded_lines': previous_options and previous_options.get('unfolded_lines') or [],
            'fully_paid': previous_options and previous_options.get('fully_paid') or False,
            'payment_date_filter': previous_options and previous_options.get('payment_date_filter') or False,
            # 'invoice_date_filter': not(previous_options and previous_options.get('payment_date_filter') or False),
        }

        # print(options)

        # Multi-company is there for security purpose and can't be disabled by a filter.
        self._init_filter_multi_company(options, previous_options=previous_options)

        # Call _init_filter_date/_init_filter_comparison because the second one must be called after the first one.
        if self.filter_date:
            self._init_filter_date(options, previous_options=previous_options)
        if self.filter_comparison:
            self._init_filter_comparison(options, previous_options=previous_options)
        if self.filter_analytic:
            options['analytic'] = self.filter_analytic

        filter_list = [attr for attr in dir(self)
                       if (attr.startswith('filter_') or attr.startswith('order_')) and attr not in (
                       'filter_date', 'filter_comparison') and len(attr) > 7 and not callable(getattr(self, attr))]
        for filter_key in filter_list:
            options_key = filter_key[7:]
            init_func = getattr(self, '_init_%s' % filter_key, None)
            if init_func:
                init_func(options, previous_options=previous_options)
            else:
                filter_opt = getattr(self, filter_key, None)
                if filter_opt is not None:
                    if previous_options and options_key in previous_options:
                        options[options_key] = previous_options[options_key]
                    else:
                        options[filter_key[7:]] = filter_opt

        return options

    def _get_lines(self, options, line_id=None):
        lines = list()
        # print(options['date']['date_to'], options['date']['date_from'])
        # print(options)
        filters = [('state', '=', 'posted'),
                   ('type', 'in', ['out_invoice', 'out_refund'])]
        if not options['payment_date_filter']:
            filters.append(tuple(['invoice_date', '<=', options['date']['date_to']]))
            filters.append(tuple(['invoice_date', '>=', options['date']['date_from']]))
        if options['fully_paid']:
            filters.append(tuple(['amount_residual_signed', '!=', 0]))
        invoices = self.env['account.move'].search(filters, order='invoice_date desc')

        if options['payment_date_filter']:
            for inv in invoices:
                payments = inv.invoice_payments_widget
                if payments == 'false':
                    invoices -= inv
                else:
                    # print('Inside', inv)
                    payments = json.loads(payments)
                    if options['date']['date_to'] >= payments['content'][0]['date'] >= options['date']['date_from']:
                        pass
                    else:
                        invoices -= inv
        i = 1
        today = fields.Date.today()
        total_out = 0
        for inv in invoices:
            analytic_name = inv.invoice_line_ids[0].analytic_account_id.name
            inv_line1 = inv.invoice_line_ids[0]
            inv_name = inv.name
            partner_name = inv.partner_id.name
            currency_name = inv.currency_id.name
            due_date = inv.invoice_date_due
            outstanding = inv.amount_residual_signed
            payments = inv.invoice_payments_widget
            line = {'0': i, '1': partner_name, '2': 'Non-Related Company',
                    '3': analytic_name, '4': inv.partner_id.category_id.name, '5': '',
                    '6': inv.invoice_line_ids[0].name, '7': inv_name,
                    '8': datetime.strptime(str(inv.invoice_date), '%Y-%m-%d').strftime('%d-%m-%Y'),
                    '9': inv.po_no or '-', '10': inv.program or '-', '11': currency_name, '12': inv_line1.points or '-',
                    '13': 'Calc', '14': round(inv_line1.price_unit, 2), '15': 'Calc',
                    '16': round(inv.amount_tax, 2) or '0', '17': '0',
                    '18': '0', '19': '-', '20': '0', '21': '-', '22': '0', '23': '0',
                    '24': round(outstanding, 2), '25': inv.invoice_payment_term_id.name,
                    '26': datetime.strptime(str(due_date), '%Y-%m-%d').strftime('%d-%m-%Y') or '-', '27': '-',
                    '28': '-', '29': analytic_name,
                    }
            if partner_name:
                if partner_name[:2] == 'BI':
                    line['2'] = 'Related Company'
            if currency_name == 'USD':
                line['13'] = round(inv.amount_total, 2)
            else:
                line['13'] = '-'
            line['15'] = round(inv.amount_untaxed_signed, 2)
            line['17'] = round(inv.amount_total_signed, 2)
            if payments != 'false':
                # print(type(payments))
                payments = json.loads(payments)
                line['18'] = payments['content'][0]['amount']
                if payments['content'][0]['currency'] == '$':
                    line_move = self.env['account.move.line'].search([('payment_id', '=', payments['content'][0]['account_payment_id'])])
                    if line_move:
                        line['18'] = line_move[0].debit or line_move[0].credit
                line['19'] = datetime.strptime(str(payments['content'][0]['date']), '%Y-%m-%d').strftime('%d-%m-%Y')
                if len(payments['content']) > 1:
                    line['20'] = payments['content'][1]['amount']
                    if payments['content'][1]['currency'] == '$':
                        line_move = self.env['account.move.line'].search([('payment_id', '=', payments['content'][1]['account_payment_id'])])
                        if line_move:
                            line['20'] = line_move[0].debit or line_move[0].credit
                    line['21'] = datetime.strptime(str(payments['content'][1]['date']), '%Y-%m-%d').strftime('%d-%m-%Y')
                # print(payments)
            if due_date:
                # print(due_date)
                fmt = '%Y-%m-%d'
                d1 = datetime.strptime(str(today), fmt)
                d2 = datetime.strptime(str(due_date), fmt)
                date_dif = (d1 - d2).days
                line['27'] = date_dif
                if date_dif <= 0:
                    line['28'] = 'Within the Due'
                elif date_dif <= 30:
                    line['28'] = '<30 Days'
                elif date_dif <= 60:
                    line['28'] = '<60 Days'
                elif date_dif <= 90:
                    line['28'] = '<90 Days'
                elif date_dif <= 120:
                    line['28'] = '<120 Days'
                elif date_dif <= 180:
                    line['28'] = '<180 Days'
                elif date_dif <= 365:
                    line['28'] = '<365 Days'
                else:
                    line['28'] = '>365 Days'

            tds = 0
            acc = self.env['account.account'].search([('name', '=', 'TDS Receivables')])
            move_lines = self.env['account.move.line'].search([('ref', '=', inv_name), ('account_id', '=', acc.id)])
            for move in move_lines:
                tds += move.debit
            line['22'] = tds

            bank = 0
            acc = self.env['account.account'].search([('name', '=', 'Bank Charges')])
            move_lines = self.env['account.move.line'].search([('ref', '=', inv_name), ('account_id', '=', acc.id)])
            for move in move_lines:
                bank += move.debit
            line['23'] = bank
            lines.append(line)
            i += 1

        advance_payment = self.env['account.payment'].search(['|', ('payment_receivable', '=', 'advance'), ('communication', 'ilike', 'Advance payment Received'),])
        for pay in advance_payment:
            total_amount = 0
            for reconciled in pay.reconciled_invoice_ids:
                payments = reconciled.invoice_payments_widget
                payments = json.loads(payments)
                payment_details = payments['content']
                amount = list(filter(lambda payment: payment.get('account_payment_id') == pay.id, payment_details))
                # print(amount, amount[0].get('amount'))
                if amount:
                    total_amount += amount[0].get('amount')
                else:
                    total_amount += 0
            outstanding = pay.amount-total_amount
            analytic_name = pay.analytic_account_id.name
            inv_name = pay.communication
            partner_name = pay.partner_id.name
            currency_name = pay.currency_id.name
            advance = {'0': i, '1': partner_name, '2': 'Non-Related Company',
                    '3': analytic_name, '4': pay.partner_id.category_id.name, '5': '',
                    '6': inv_name, '7': pay.name,
                    '8': datetime.strptime(str(pay.payment_date), '%Y-%m-%d').strftime('%d-%m-%Y'),
                    '9': '-', '10': '-', '11': currency_name, '12': '-',
                    '13': '-', '14': '-', '15': '-',
                    '16': '-', '17': '-',
                    '18': pay.amount, '19': '-', '20': '-', '21': '-', '22': '-', '23': '-',
                    '24': -round(outstanding, 2) or 0.0, '25': '-',
                    '26': '-', '27': '-',
                    '28': '-', '29': '',
                    }
            if partner_name:
                if partner_name[:2] == 'BI':
                    line['2'] = 'Related Company'
            lines.append(advance)
            i += 1
        return lines

    def get_html(self, options, line_id=None, additional_context=None):
        rcontext = {'lines': self._get_lines(options),
                    'header_columns': self._get_columns_name(options),
                    'options': options}
        html = self.env['ir.ui.view'].render_template(
            "prixgen_custom_aged_receivable_email.sales_register_template",
            values=dict(rcontext),
        )
        return html

    def _get_report_name(self):
        return _("Sales Register")

    def get_xlsx(self, options, response=None):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'strings_to_formulas': False,
        })
        sheet = workbook.add_worksheet(self._get_report_name())
        default_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2})
        default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 10})
        date_style = workbook.add_format({'text_wrap': True, 'num_format': 'dd mmm yyyy', 'font_name': 'Arial', 'font_size': 10})
        # print(date_style, workbook.formats)
        lines = self._get_lines(options)
        header_cols = self._get_columns_name(options)
        for i in range(len(header_cols)):
            sheet.set_column(0, i, 18)
            sheet.write(0, i, header_cols[i]['name'], default_col1_style)
        # print(lines, lines[0])
        for j in range(len(lines)):
            for i in range(len(header_cols)):
                if i in (8, 19, 21, 26):
                    try:
                        sheet.write(j+1, i, datetime.strptime(lines[j][str(i)], '%d-%m-%Y'), date_style)
                    except:
                        sheet.write(j+1, i, lines[j][str(i)], date_style)
                else:
                    sheet.write(j+1, i, lines[j][str(i)], default_style)

        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()

        return generated_file


class ResPartner(models.Model):
    _inherit = 'account.payment'

    payment_receivable = fields.Selection([
        ('normal', 'Normal Payment'),
        ('advance', 'Advance Payment')
    ], string='Payment Type', default='normal')




