# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    rfq_subject = fields.Char('Subject', copy=False)
    client_order_ref = fields.Char(string='Client PO Number',copy=False)
    rfq_incoterm_id = fields.Many2one('account.incoterms', 'Incoterm', states={'done': [('readonly', True)]}, help="International Commercial Terms are a series of predefined commercial terms used in international transactions.", copy=False)
    rfq_payment_term_id = fields.Many2one('account.payment.term', 'Payment Terms', copy=False)
    rfq_fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position', copy=False)
    rfq_notes = fields.Text('Terms and Conditions', copy=False)
    created_rfq_ids = fields.Many2many('purchase.order', 'sale_rfq', 'sale_id', 'rfq_id', 'Created RFQs.', readonly=1, copy=False)

    res_purchase_id_sale = fields.Many2one('res.purchase.order', string="Purchase Reference")
    res_po_move_sale = fields.One2many('res.purchase.order', 'partner_id', string="Purchase Order",
                                       related='partner_id.res_po')
    account_value_sale = fields.Monetary(string="Purchase Value", related="res_purchase_id_sale.purchase_value_po")
    account_validity_sale = fields.Date(string="Purchase Validity", related="res_purchase_id_sale.purchase_validity_po")
    account_utilize_po_sale = fields.Monetary(string="Amount Utilize", compute="onchange_account_available")
    account_available_sale = fields.Monetary(string="Amount Available",
                                             related="res_purchase_id_sale.purchase_value_remains")


    @api.onchange('res_purchase_id_sale')
    def onchange_po_no(self):
        self.po_no = self.res_purchase_id_sale.name

    def onchange_account_available(self):
        for rec in self:
            rec.account_utilize_po_sale = rec.account_value_sale - rec.account_value_sale

    #Create RFQ Button : Header
    def LoadWizardForQuotationToRFQ(self):
        self.ensure_one()
        IrModelData = self.env['ir.model.data']
        view = IrModelData.get_object_reference('po_from_quotation', 'view_rfq_from_quotation_wizard')
        view_id = view and view[1] or False
        vals =  {
            'name': _('Create RFQ'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'res_model': 'rfq.from.quotation',
            'target': 'new',
        }
        return vals


class AccountMoveNewField(models.Model):
    _inherit = 'account.move'

    grn_number_account = fields.Many2many('stock.picking', 'name', string='GRN Number')
    client_po_acc = fields.Char('Client PO Number', compute='_compute_client_po_no_acc')

    def _compute_client_po_no_acc(self):
        sale_order = self.env['sale.order'].search([])
        for rec in sale_order:
            if rec.name == self.invoice_origin:
                self.client_po_acc = rec.client_order_ref

        return self.client_po_acc

    def _validate_move_modification(self):
        pass

class ProductTemplateValidation(models.Model):
    _inherit = 'product.template'

    @api.constrains('l10n_in_hsn_code')
    def _validate_hsn_code(self):
        for rec in self:
            if rec.l10n_in_hsn_code:
                if rec.l10n_in_hsn_code.isdigit():
                    length = len(rec.l10n_in_hsn_code)
                    if length > 8 or length < 6:
                        raise ValidationError("HSN Code Invalid")
            else:
                return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
