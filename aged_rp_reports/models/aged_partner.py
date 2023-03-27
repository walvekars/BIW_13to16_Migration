# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields, _
from odoo.tools.misc import format_date
from dateutil.relativedelta import relativedelta
from datetime import datetime


class AccountMove(models.Model):
    _inherit = 'account.move'


    def update_analytic_account(self):
        invoices = self.env['account.move'].browse(self._context.get('active_ids', []))
        for each in invoices:
            analytic_accounts = list(set(each.invoice_line_ids.mapped('analytic_account_id')))
            if len(analytic_accounts) == 1:
                for line in each.line_ids:
                    line.analytic_account_id = analytic_accounts[0].id


        # return True


class report_account_aged_partner(models.AbstractModel):
    _inherit = "account.aged.partner"


    def _get_columns_name(self, options):
        columns = [
            {},
            {'name': _("Partner Tag"), 'class': '', 'style': 'text-align:center; white-space:nowrap;'},
            {'name': _("Analytic Account"), 'class': '', 'style': 'text-align:center; white-space:nowrap;'},
            {'name': _("Due Date"), 'class': 'date', 'style': 'white-space:nowrap;'},
            {'name': _("Journal"), 'class': '', 'style': 'text-align:center; white-space:nowrap;'},
            {'name': _("Account"), 'class': '', 'style': 'text-align:center; white-space:nowrap;'},
            {'name': _("Exp. Date"), 'class': 'date', 'style': 'white-space:nowrap;'},
            {'name': _("As of: %s") % format_date(self.env, options['date']['date_to']), 'class': 'number sortable', 'style': 'white-space:nowrap;'},
            {'name': _("1 - 30"), 'class': 'number sortable', 'style': 'white-space:nowrap;'},
            {'name': _("31 - 60"), 'class': 'number sortable', 'style': 'white-space:nowrap;'},
            {'name': _("61 - 90"), 'class': 'number sortable', 'style': 'white-space:nowrap;'},
            {'name': _("91 - 180"), 'class': 'number sortable', 'style': 'white-space:nowrap;'},
            {'name': _("180 - 365"), 'class': 'number sortable', 'style': 'white-space:nowrap;'},
            {'name': _("Older"), 'class': 'number sortable', 'style': 'white-space:nowrap;'},
            {'name': _("Total"), 'class': 'number sortable', 'style': 'white-space:nowrap;'},
        ]
        return columns


    @api.model
    def _get_lines(self, options, line_id=None):
        sign = -1.0 if self.env.context.get('aged_balance') else 1.0
        lines = []
        analytic_accounts = False
        account_types = [self.env.context.get('account_type')]
        context = {'include_nullified_amount': True}
        if line_id and 'partner_' in line_id:
            # we only want to fetch data about this partner because we are expanding a line
            partner_id_str = line_id.split('_')[1]
            if partner_id_str.isnumeric():
                partner_id = self.env['res.partner'].browse(int(partner_id_str))
            else:
                partner_id = False
            context.update(partner_ids=partner_id)
        if options.get('analytic_accounts'):
            analytic_accounts = options.get('analytic_accounts')
        results, total, amls = self.env['report.account.report_agedpartnerbalance']. with_context(**context)._get_partner_move_lines(account_types, self._context['date_to'], 'posted', 30, analytic_accounts)
        # results, total, amls = self.env['report.account.report_agedpartnerbalance'].with_context(**context)._get_partner_move_lines(account_types, self._context['date_to'], 'posted', 30)

        grand_total_paid = 0
        for values in results:
#             payments = self.env['account.payment'].search([('partner_id', '=', values['partner_id']),
#                                                            ('payment_date', '>',
#                                                             datetime.strptime(options['date']['date_to'], '%Y-%m-%d')
#                                                             - relativedelta(days=8)),
#                                                            ('payment_date', '<=',
#                                                             datetime.strptime(options['date']['date_to'], '%Y-%m-%d')),
#                                                            ('payment_type', '=', 'inbound'),
#                                                            ('state', 'not in', ['draft', 'cancelled'])])
#             total_paid = 0
            # for payment in payments:
            #     total_paid += payment.amount
#             total_paid = sum([payment.amount for payment in payments])
#             grand_total_paid += total_paid
            vals = {
                'id': 'partner_%s' % (values['partner_id'],),
                'name': values['name'],
                'level': 2,
                'columns': [{'name': ''}] * 6 + [{'name': self.format_value(sign * v), 'no_format': sign * v}
                                                 for v in [values['direction'], values['5'], values['4'],
                                                           values['3'], values['2'],
                                                           values['1'], values['0'], values['total']]],
                'trust': values['trust'],
                'unfoldable': True,
                'unfolded': 'partner_%s' % (values['partner_id'],) in options.get('unfolded_lines'),
                'partner_id': values['partner_id'],
#                 'last_week_amt': total_paid,
            }
            lines.append(vals)
            if 'partner_%s' % (values['partner_id'],) in options.get('unfolded_lines'):
                for line in amls[values['partner_id']]:
                    aml = line['line']
                    if aml.move_id.is_purchase_document():
                        caret_type = 'account.invoice.in'
                    elif aml.move_id.is_sale_document():
                        caret_type = 'account.invoice.out'
                    elif aml.payment_id:
                        caret_type = 'account.payment'
                    else:
                        caret_type = 'account.move'

                    line_date = aml.date_maturity or aml.date

                    if not self._context.get('no_format'):
                        line_date = format_date(self.env, line_date)
                    vals = {
                        'id': aml.id,
                        'name': aml.move_id.name,
                        'class': 'date',
                        'caret_options': caret_type,
                        'level': 4,
                        'parent_id': 'partner_%s' % (values['partner_id'],),
                        'columns': [{'name': v} for v in [aml.tags_name,aml.analytic_account_id.name or aml.analytic_account_id.display_name,format_date(self.env, aml.date_maturity or aml.date), aml.journal_id.code, aml.account_id.display_name, format_date(self.env, aml.expected_pay_date)]] +
                                   [{'name': self.format_value(sign * v, blank_if_zero=True), 'no_format': sign * v} for v in [line['period'] == 7-i and line['amount'] or 0 for i in range(7)]],
                        'action_context': {
                            'default_type': aml.move_id.type,
                            'default_journal_id': aml.move_id.journal_id.id,
                        },
                        'title_hover': self._format_aml_name(aml.name, aml.ref, aml.move_id.name),
                    }
                    lines.append(vals)
        if total and not line_id:
            total_line = {
                'id': 0,
                'name': _('Total'),
                'class': 'total',
                'level': 2,
                'columns': [{'name': ''}] * 6 + [{'name': self.format_value(sign * v), 'no_format': sign * v} for v in [total[7], total[5], total[4], total[3], total[2], total[1], total[0], total[6]]],
#                 'last_week_amt': grand_total_paid,
            }
            lines.append(total_line)
        return lines


