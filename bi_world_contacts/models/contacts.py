from odoo.exceptions import UserError
from odoo import api, fields, models, _
from num2words import num2words
import pdb
import json

class Contacts(models.Model):
    _inherit = 'res.partner'

    contact_analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account")
    email_grouping = fields.Boolean(string='Email Group', default=False)
    # analytic_distribution = fields.Json(
    #     inverse="_inverse_analytic_distribution",
    # )







