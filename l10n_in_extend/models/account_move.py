# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    tax_amount_by_lines = fields.Binary(string='Tax amount for lines',
        compute='_compute_invoice_taxes_by_line_by_group',
        help='Tax amount by group for the invoice line.')

    l10n_in_extend_state_id = fields.Many2one('res.country.state', string="Location of supply")
    dispatch_partner_id = fields.Many2one("res.partner", string="Dispatch Address",
        readonly=True, states={'draft': [('readonly', False)]},
        help="Dispatch address for current invoice/bill.")

    def _compute_invoice_taxes_by_line_by_group(self):
        for invoice in self:
            taxes = dict()
            for line in invoice.invoice_line_ids:
                taxes[line.id] = line.tax_amount_by_tax_group
            invoice.tax_amount_by_lines = taxes

    @api.model
    def _get_tax_grouping_key_from_tax_line(self, tax_line):
        res = super()._get_tax_grouping_key_from_tax_line(tax_line)
        if tax_line.move_id.journal_id.company_id.country_id.code != 'IN':
            return res

        res.update({
            'base_line_ref': tax_line.base_line_ref,
        })
        return res

    @api.model
    def _get_tax_grouping_key_from_base_line(self, base_line, tax_vals):
        res = super()._get_tax_grouping_key_from_base_line(base_line, tax_vals)
        if base_line.move_id.journal_id.company_id.country_id.code != 'IN':
            return res

        ref = base_line._origin.id or base_line.id.ref or base_line.id
        base_line.base_line_ref = ref
        res.update({
            'base_line_ref': ref,
        })
        return res

    @api.model
    def _get_tax_key_for_group_add_base(self, line):
        tax_key = super(AccountMove, self)._get_tax_key_for_group_add_base(line)
        if line.move_id.journal_id.company_id.country_id.code != 'IN':
            return tax_key
        tax_key += [line.id,]
        return tax_key

    @api.model
    def _l10n_in_get_indian_state(self, partner):
        """In tax return filing, If customer is not Indian in that case place of supply is must set to Other Territory.
        So we set Other Territory in l10n_in_extend_state_id when customer(partner) is not Indian
        Also we raise if state is not set in Indian customer.
        State is big role under GST because tax type is depend on.for more information check this https://www.cbic.gov.in/resources//htdocs-cbec/gst/Integrated%20goods%20&%20Services.pdf"""
        if partner.country_id and partner.country_id.code == 'IN' and not partner.state_id:
            raise ValidationError(_("State is missing from address in '%s'. First set state after post this invoice again." %(partner.name)))
        elif partner.country_id and partner.country_id.code != 'IN':
            return self.env.ref('l10n_in_extend.state_in_oc')
        return partner.state_id

    def post(self):
        """Use journal type to define document type because not miss state in any entry including POS entry"""
        res = super().post()
        for move in self.filtered(lambda m: m.company_id.country_id.code == 'IN'):
            """Check state is set in company/sub-unit"""
            company_unit_partner = move.journal_id.l10n_in_gstin_partner_id or move.journal_id.company_id
            if not company_unit_partner.state_id:
                raise ValidationError(_("State is missing from your company/unit %s(%s).\nFirst set state in your company/unit." % (company_unit_partner.name, company_unit_partner.id)))
            elif move.journal_id.type == 'purchase':
                move.l10n_in_extend_state_id = company_unit_partner.state_id

            shipping_partner = shipping_partner = ('partner_shipping_id' in move) and move.partner_shipping_id or move.partner_id
            if move.journal_id.type == 'sale':
                move.l10n_in_extend_state_id = self._l10n_in_get_indian_state(shipping_partner)
                if not move.l10n_in_extend_state_id:
                    move.l10n_in_extend_state_id = self._l10n_in_get_indian_state(move.partner_id)
                #still state is not set then assumed that transaction is local like PoS so set state of company unit
                if not move.l10n_in_extend_state_id:
                    move.l10n_in_extend_state_id = company_unit_partner.state_id
        return res


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # it would be good to use the many2one fields instead of char, but required
    # framework fix for onchnage/create, we just need the referance to search the
    # related tax lines so char field would be ok as of now.
    base_line_ref = fields.Char('Matching Ref',
        help='Technical field to map invoice base line with its tax lines.')
    
    tax_amount_by_tax_group = fields.Binary(string='Tax amount by group',
        compute='_compute_invoice_line_taxes_by_group',
        help='Tax amount by group for the line.')
    
    def _compute_invoice_line_taxes_by_group(self):
        # prepare the dict of tax values by tax group
        # line.tax_amount_by_tax_group = {'SGST': 9.0, 'CGST': 9.0, 'Cess': 2.0}
        for line in self:
            move_id = line.move_id
            taxes = dict()
            for ln in self.search([('base_line_ref','=',str(line.id)), ('tax_line_id','!=',False), ('move_id','=',line.move_id.id)]):
                tax_group_name = ln.tax_line_id.tax_group_id.name.upper()
                if tax_group_name not in ('SGST', 'CGST', 'IGST', 'CESS', 'CESS-NON-ADVOL','STATE CESS','STATE CESS-NON-ADVOL'):
                    tax_group_name = 'OTHER'
                taxes.setdefault(tax_group_name, 0.0)
                if not self._context.get('in_company_currency') and move_id.currency_id and move_id.company_id.currency_id != move_id.currency_id:
                    taxes[tax_group_name] += ln.amount_currency * (move_id.is_inbound() and -1 or 1)
                else:
                    taxes[tax_group_name] += ln.balance * (move_id.is_inbound() and -1 or 1)
            line.tax_amount_by_tax_group = taxes

    def _update_base_line_ref(self):
        # search for the invoice lines on which the taxes applied
        base_lines = self.filtered(lambda ln: ln.tax_ids and ln.move_id.journal_id.company_id.country_id.code == 'IN')
        for line in base_lines:
            #filters the tax lines related to the base lines and replace virtual_id with the database id
            tax_lines = self.filtered(lambda ln: ln.base_line_ref == line.base_line_ref and not ln.tax_ids)
            tax_lines += line
            tax_lines.write({
                'base_line_ref': line.id,
            })

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._update_base_line_ref()
        return lines
