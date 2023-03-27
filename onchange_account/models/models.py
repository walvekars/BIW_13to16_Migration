# -*- coding: utf-8 -*-

from odoo import models, fields, api


class invoice(models.Model):
    _inherit = 'account.move'


    def change_all(self):
        for rec in self:
            rec._onchange_type()
            rec._onchange_partner_id()
            rec._onchange_partner_id_atn()

    def _onchange_type(self):
        ''' Onchange made to filter the partners depending of the type. '''
        for rec in self:
            if rec.is_sale_document(include_receipts=True):
                if self.env['ir.config_parameter'].sudo().get_param('account.use_invoice_terms'):
                    rec.narration = self.company_id.invoice_terms or self.env.company.invoice_terms



    @api.onchange('partner_id')
    def _onchange_partner_id_atn(self):
        self.attn = self.partner_id.attn
        return super(invoice, self)._onchange_partner_id()

