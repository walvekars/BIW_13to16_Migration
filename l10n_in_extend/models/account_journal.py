# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountJournal(models.Model):
    _inherit = "account.journal"

    l10n_in_extend_customer_debit_note = fields.Boolean(string='Customer Debit note',
        help='Tick this if you use this Journal as Customer Debit note.')
