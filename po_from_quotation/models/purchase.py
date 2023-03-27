# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from num2words import num2words


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    ref_so_id = fields.Many2one('sale.order', string='Order', copy=False)
    grn_number_purchase = fields.Many2many('stock.picking', 'name', compute='_compute_grn_no', string='GRN Number')
    client_po_from_quotation = fields.Char(string='Client PO Number', compute='_compute_po_number_quo')
    vendor_invoice_no = fields.Char(string='Vendor Invoice No.', compute='_compute_vendor_invoice')
    Vendor_invoice_date = fields.Date(String='Vendor Invoice Date')

    def _compute_grn_no(self):
        if self.state == 'purchase':
            stock_picking = self.env['stock.picking'].search([])
            rec_ids = []
            for rec in stock_picking:
                if self.name == rec.origin:
                    rec_ids.append(rec.id)
                    # if self.client_po_from_quotation:
                    rec.client_po_stock = self.client_po_from_quotation

            self.grn_number_purchase = rec_ids

        else:
            return self.grn_number_purchase

    def _compute_po_number_quo(self):
        sale_order = self.env['sale.order'].search([])
        for rec in sale_order:
            if self.origin == rec.name:
                self.client_po_from_quotation = rec.client_order_ref

        return self.client_po_from_quotation

    def _compute_vendor_invoice(self):
        account_move = self.env['account.move'].search([])
        for rec in account_move:
            if self.name == rec.invoice_origin:
                self.vendor_invoice_no = rec.name
                self.Vendor_invoice_date = rec.invoice_date

        return self.vendor_invoice_no

    def action_view_invoice(self):
        # return super(PurchaseOrder, self).action_view_invoice()
        '''
        This function returns an action that display existing vendor bills of given purchase order ids.
        When only one found, show the vendor bill immediately.
        '''
        action = self.env.ref('account.action_move_in_invoice_type')
        result = action.read()[0]
        create_bill = self.env.context.get('create_bill', False)
        # override the context to get rid of the default filtering
        result['context'] = {
            'default_type': 'in_invoice',
            'default_company_id': self.company_id.id,
            'default_purchase_id': self.id,
            'default_partner_id': self.partner_id.id,
            'default_grn_number_account': self.grn_number_purchase.ids,
            'default_client_po_acc': self.client_po_from_quotation
        }
        # Invoice_ids may be filtered depending on the user. To ensure we get all
        # invoices related to the purchase order, we read them in sudo to fill the
        # cache.
        self.sudo()._read(['invoice_ids'])
        # choose the view_mode accordingly
        if len(self.invoice_ids) > 1 and not create_bill:
            result['domain'] = "[('id', 'in', " + str(self.invoice_ids.ids) + ")]"
        else:
            res = self.env.ref('account.view_move_form', False)
            form_view = [(res and res.id or False, 'form')]
            if 'views' in result:
                result['views'] = form_view + [(state, view) for state, view in action['views'] if
                                               view != 'form']
            else:
                result['views'] = form_view
            # Do not set an invoice_id if we want to create a new bill.
            if not create_bill:
                result['res_id'] = self.invoice_ids.id or False
        result['context']['default_invoice_origin'] = self.name
        result['context']['default_ref'] = self.partner_ref
        return result

    def amt_to_text(self, total):
        amt_txt = num2words(total)
        amt_upp = amt_txt.upper()
        return amt_upp


class ProcurementGroup(models.Model):
    _inherit = "procurement.group"

    @api.model
    def create(self, vals):
        name = vals.get('name')
        po_order = self.env['purchase.order'].search([('name', '=', str(name))])
        if po_order and po_order.ref_so_id:
            vals.update({'sale_id': po_order.ref_so_id.id})
        res = super(ProcurementGroup, self).create(vals)
        return res


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    so_line_id = fields.Many2one('sale.order.line', string='SaleOrderLine', copy=False)  # Ref of SO LINE


class StockPickingNewField(models.Model):
    _inherit = "stock.picking"

    client_po_stock = fields.Char(string='Client PO Number',)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
