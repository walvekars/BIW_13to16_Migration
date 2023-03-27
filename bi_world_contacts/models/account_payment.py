from odoo.exceptions import UserError
from odoo import api, fields, models, _
from num2words import num2words
import pdb


class AccountPayment(models.Model):
    _inherit = "account.payment"

    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account", readonly=False)

    @api.model
    def default_get(self, default_fields):
        rec = super(AccountPayment, self).default_get(default_fields)
        if rec.get('partner_id'):
            partner = self.env['res.partner'].browse(rec.get('partner_id'))
            if partner.contact_analytic_account_id:
                rec.update({'analytic_account_id': partner.contact_analytic_account_id.id})
        return rec
    
    @api.onchange('partner_id')
    def analytic_account_id_onchange_partner(self):
        if self.partner_id:
            self.analytic_account_id = self.partner_id.contact_analytic_account_id
