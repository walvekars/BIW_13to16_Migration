# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class RFQFromQuotation(models.TransientModel):
    _name = 'rfq.from.quotation'
    _description = 'Create RFQ From Quotation Wizard'

    #GET DEFAULT VALUES FROM QUOTATIONS
    @api.model
    def default_get(self, fields):
        context = dict(self._context or {})
        active_model = context.get('active_model')
        active_id = context.get('active_id')
        #Checks on context parameters
        if not active_model or not active_id:
            raise UserError(_("Programmation error: wizard action executed without active_model or active_ids in context."))
        if active_model != 'sale.order':
            raise UserError(_("Programmation error: the expected model for this action is 'sale.order'. The provided one is '%d'.") % active_model)

        SaleOrder = self.env['sale.order']
        POLine = self.env['purchase.order.line']

        order_obj = SaleOrder.browse(active_id)
        order_line_list = []
        OrderlinewithRemaingQuantity = False
        for line in order_obj.order_line:
            if line.display_type:
                order_line_list.append((0,0,{
                    'display_type': line.display_type,
                    'name': line.name,
                    'so_line_id': line.id,
                }))
            po_line_objs = POLine.search([('so_line_id','=',line.id),
                                          ('state','in',['purchase','done']),
                                          ('order_id.ref_so_id','=',order_obj.id)])
            convert_qty = 0
            for po_line in po_line_objs:
                convert_qty += po_line.product_uom._compute_quantity(po_line.product_qty, line.product_uom, rounding_method='HALF-UP')
            product_uom_qty = line.product_uom_qty - convert_qty
            if product_uom_qty > 0:
                order_line_list.append((0,0,{
                    'display_type': False,
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'remaining_qty': product_uom_qty,
                    'product_uom_qty': product_uom_qty,
                    'product_uom': line.product_uom.id,
                    'price_unit': line.price_unit,
                    'so_line_id': line.id,
                }))
                OrderlinewithRemaingQuantity = True

        #Manage Section and Notes
        data = []
        for record in order_line_list:
            data.append(record[2])
        index = 0
        last = ''
        new_list = []
        length = 1
        for record in data:
            if record.get('display_type') == 'line_section':
                if record.get('display_type') == last:
                    #Delete Vals
                    for i in range(len(new_list)):
                        if new_list[i]['temp'] == index:
                            del new_list[i] 
                            break
                last = record.get('display_type')
                index += 1
                record.update({'temp': index})
                new_list.append(record)
            elif record.get('display_type') == 'line_note':
                if last == False or last == 'line_note' or last == 'line_section':
                    index += 1
                    last = record.get('display_type')
                    record.update({'temp': index})
                    new_list.append(record)
            else:
                index += 1
                last = record.get('display_type')
                record.update({'temp': index})
                new_list.append(record)
            length += 1
        final_list = []
        for new in new_list:
            del new['temp']
            final_list.append((0,0,new))
        #End of Manage Section and Notes

        if not OrderlinewithRemaingQuantity:
            raise UserError(_("There is no any Order line with Remaing Quantity."))
        res = super(RFQFromQuotation, self).default_get(fields)
        res.update({
            'quotation_id': order_obj.id,
            'rfq_subject': order_obj.rfq_subject,
            'rfq_incoterm_id': order_obj.rfq_incoterm_id.id or False,
            'rfq_payment_term_id': order_obj.rfq_payment_term_id.id or False,
            'rfq_fiscal_position_id': order_obj.rfq_fiscal_position_id.id or False,
            'rfq_currency_id': order_obj.currency_id.id or False,
            'rfq_notes': order_obj.rfq_notes,
            'order_lines': final_list,
        })
        return res

    #FIELDS DECLARATION
    quotation_id = fields.Many2one('sale.order', string='Quotation', readonly=1)
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], related='quotation_id.state', string='Order Status', readonly=True)
    raise_rfq_for = fields.Selection([('all_items', 'All Items'),('only_selected_items', 'Only Selected Items')], string='Raise RFQ For', required=1, default='all_items')
    rfq_vendor_id = fields.Many2one('res.partner', string='Vendor', required=1)
    rfq_partner_ref = fields.Char('Vendor Reference',\
        help="Reference of the sales order or bid sent by the vendor. "
             "It's used to do the matching when you receive the "
             "products as this reference is usually written on the "
             "delivery order sent by your vendor.")
    rfq_subject = fields.Char('Subject')
    rfq_incoterm_id = fields.Many2one('account.incoterms', 'Incoterm', required=1, help="International Commercial Terms are a series of predefined commercial terms used in international transactions.")
    rfq_payment_term_id = fields.Many2one('account.payment.term', 'Payment Terms', required=1)
    rfq_fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position', required=1)
    rfq_currency_id = fields.Many2one("res.currency", string="Currency", required=True)
    rfq_notes = fields.Text('Terms and Conditions')
    order_lines = fields.One2many('quotation.order.line', 'line_id', string='Order Lines')

    #CONFIRM BUTTON
    def CreateRFQ(self):
        PurchaseOrder = self.env['purchase.order']
        for wizard in self:
            if wizard.raise_rfq_for == 'only_selected_items':
                lines = wizard.order_lines.filtered(lambda r: r.select_item == True)
                if not lines:
                    raise UserError(_("Please select items because you select Raise RFQ For 'Only Selected Items'."))
                section_list = []
                selected_list = []
                po_list = []
                for l in wizard.order_lines:
                    if l.display_type == 'line_section':
                        section_list.clear()
                        section_list.append(l)
                    if not l.display_type:
                        if l.select_item:
                            if section_list:
                                if section_list[0] not in po_list:
                                    po_list.append(section_list[0])
                            po_list.append(l)
                            selected_list.clear()
                            selected_list.append(l)
                        else:
                            selected_list.clear()
                    if l.display_type == 'line_note':
                        if selected_list:
                            po_list.append(l)
                lines = po_list

            if wizard.raise_rfq_for == 'all_items':
                lines = wizard.order_lines

            po_line_list = []
            for line in lines:
                if line.display_type:
                    po_line_list.append((0,0,{
                        'display_type': line.display_type,
                        'name': line.name,
                        'product_qty': line.product_uom_qty,
                        'so_line_id': line.so_line_id.id,
                    }))
                else:
                    tax_list = []
                    sale_order_id = False
                    sale_line_id = False

                    taxes = line.product_id.supplier_taxes_id.filtered(lambda r: not line.so_line_id.company_id or r.company_id == line.so_line_id.company_id)
                    fpos = wizard.rfq_fiscal_position_id or wizard.rfq_vendor_id.property_account_position_id
                    seller = wizard.rfq_vendor_id
                    taxes_id = fpos.map_tax(taxes, line.product_id, seller.name) if fpos else taxes
                    if taxes_id:
                        tax_list = taxes_id.filtered(lambda x: x.company_id.id == wizard.quotation_id.company_id.id).ids

                    sale_order_id = wizard.quotation_id.id
                    sale_line_id = line.so_line_id.id

                    po_line_list.append((0,0,{
                        'product_id': line.product_id.id,
                        'name': line.name,
                        'date_planned': fields.Datetime.now(),
                        'product_qty': line.product_uom_qty,
                        'product_uom': line.product_uom.id,
                        'price_unit': line.price_unit,
                        'so_line_id': line.so_line_id.id,
                        'taxes_id': [(6, 0, tax_list)],
                        'sale_order_id': sale_order_id,
                        'sale_line_id': sale_line_id,
                        }))
            po_vals = {
                'partner_id': wizard.rfq_vendor_id.id,
                'date_order': fields.Datetime.now(),
                'partner_ref': wizard.rfq_partner_ref,
                'origin': wizard.quotation_id.name,
                'ref_so_id': wizard.quotation_id.id,#Its ust for Ref
                'incoterm_id': wizard.rfq_incoterm_id.id or False,
                'payment_term_id': wizard.rfq_payment_term_id.id or False,
                'fiscal_position_id': wizard.rfq_fiscal_position_id.id or False,
                'currency_id': wizard.rfq_currency_id.id or False,
                'notes': wizard.rfq_notes,
                'order_line': po_line_list,
            }
            created_new_rfq = PurchaseOrder.create(po_vals)
            #ADD REF OF CREATED RFQ IN QUOTATION-SALEORDER
            ref_rfq_ids = []
            for rfq_id in wizard.quotation_id.created_rfq_ids:
                ref_rfq_ids.append(rfq_id.id)
            ref_rfq_ids.append(created_new_rfq.id)

            #Set journal
            created_new_rfq.l10n_in_onchange_company_id()
            wizard.quotation_id.write({
                'created_rfq_ids': [(6, 0, ref_rfq_ids)],
            })

        context = dict(self._context or {})
        active_model = context.get('active_model')
        active_id = context.get('active_id')

        SaleOrder = self.env['sale.order']
        order_obj = SaleOrder.browse(active_id)

        self.env["mail.message"].create({
            'model':'purchase.order',
            'res_id':created_new_rfq.id,
            'body': _('This RFQ has been created from: %s') % (order_obj.name),
            'message_type':'notification',
            'author_id':self.env.user.partner_id.id,
            'email_from':self.env.user.partner_id.email,})

        self.env["mail.message"].create({
            'model':'sale.order',
            'res_id':order_obj.id,
            'body': _('RFQ: %s has been created from: %s') % (created_new_rfq.name, order_obj.name),
            'message_type':'notification',
            'author_id':self.env.user.partner_id.id,
            'email_from':self.env.user.partner_id.email,})

        return {
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
            'context': {},
            'view_mode': 'form',
            'view_type': 'form',
            'view_id': self.env.ref("purchase.purchase_order_form").id,
            'target': 'current',
            'res_id': created_new_rfq.id,
        }


class QuotationOrderLine(models.TransientModel):
    _name = "quotation.order.line"
    _description = 'Quotation line in Wizard for create RFQ'

    line_id = fields.Many2one('rfq.from.quotation', string='Order Lines')#O2M
    so_line_id = fields.Many2one('sale.order.line', string='SaleOrderLine', required=1)#Ref of SO LINE
    select_item = fields.Boolean("Select Item")
    product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)],)
    name = fields.Text(string='Description', required=True)
    remaining_qty = fields.Float(string='Remaining Qty', digits='Product Unit of Measure', readonly=True, required=True)
    product_uom_qty = fields.Float(string='Quantity to be ordered', digits='Product Unit of Measure', required=True)
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure')
    price_unit = fields.Float('Unit Price', required=True, digits='Product Price', default=0.0)
    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False, help="Technical field for UX purpose.")

    @api.model
    def create(self,vals):
        vals.update({'remaining_qty':vals.get('product_uom_qty')})
        #remaining qty is readonly field and it's value is not passing when create.
        #So passed it in the vals.
        return super(QuotationOrderLine,self).create(vals)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
