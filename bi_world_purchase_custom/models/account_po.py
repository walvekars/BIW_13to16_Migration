from odoo.exceptions import UserError, ValidationError, MissingError
from odoo import api, fields, models, _
from num2words import num2words
import pdb


class Contacts(models.Model):
    _inherit = 'account.move'

    # purchase_id = fields.Many2one('res.purchase.order', string="old Purchase Reference")
    res_purchase_id = fields.Many2one('res.purchase.order', string="Purchase Reference")
    res_po_move = fields.One2many('res.purchase.order', 'partner_id', string="Purchase Order", related='partner_id.res_po')
    account_value = fields.Monetary(string="Purchase Value",  related="res_purchase_id.purchase_value_po")
    account_validity = fields.Date(string="Purchase Validity" , related="res_purchase_id.purchase_validity_po")
    account_utilize_po = fields.Monetary(string="Amount Utilize", compute="onchange_account_available")
    account_available = fields.Monetary(string="Amount Available", related="res_purchase_id.purchase_value_remains")

    # def new_po_field(self):
    #     selected_ids = self.env.context.get('active_ids', [])
    #     selected_records = self.env['account.move'].browse(selected_ids)
    #     for rec in selected_records:
    #         if rec.purchase_id:
    #             rec.res_purchase_id = rec.purchase_id


    @api.onchange('invoice_date', 'res_purchase_id')
    def onchange_invoice_date(self):
        if self.account_validity:
            if self.account_validity < self.invoice_date:
                raise ValidationError(_('The purchase order date expired...!!'))

    @api.onchange('res_purchase_id')
    def onchange_po_no(self):
        self.po_no = self.res_purchase_id.name

    def onchange_account_available(self):
        for rec in self:
            rec.account_utilize_po = rec.account_value - rec.account_available
            
    def write(self, vals):
        for rec in self:
            res_purchase_id = vals.get('res_purchase_id')
            if res_purchase_id:
                purchase = self.env['res.purchase.order'].browse(res_purchase_id)
                if purchase and purchase.purchase_value_remains < rec.amount_untaxed:
                    raise ValidationError(_('The Invoice cannot be raised for amount exceeding the available amount' +
                                            ' on the purchase order'))
        return super(Contacts, self).write(vals)
            
#     def write(self, vals):
#         for rec in self:
#             if rec.account_available < 0:
#                 return False

#         return super(Contacts, self).write(vals)


class ContactsLine(models.Model):
    _inherit = 'account.move.line'

    def write(self, vals):
        for rec in self:
            if rec.move_id and rec.move_id.account_available < 0:
                return False

        return super(ContactsLine, self).write(vals)








