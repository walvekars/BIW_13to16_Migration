from odoo.exceptions import UserError
from odoo import api, fields, models, _
from num2words import num2words
import pdb


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.model
    def default_get(self, default_fields):
        # OVERRIDE
        values = super(AccountMoveLine, self).default_get(default_fields)
        if values.get('partner_id'):
            partner = self.env['res.partner'].browse(values.get('partner_id'))
            if partner.contact_analytic_account_id:
                values.update({'analytic_account_id': partner.contact_analytic_account_id.id})
        return values