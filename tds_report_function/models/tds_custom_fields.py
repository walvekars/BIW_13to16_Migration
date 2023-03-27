from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError,Warning
from odoo.exceptions import  ValidationError
import pdb



class AccountTds(models.Model):
	_name = 'account.tds'

	name= fields.Char(string="Name")


class AccounttdsSection(models.Model):
	_name = 'account.tds.section'

	name= fields.Char(string="Name")

class TdsNatureOfDeduction(models.Model):
	_name = 'tds.nature.deduction'

	name= fields.Char(string="Name")

class AssesseeCode(models.Model):
	_name = 'assessee.code'

	name= fields.Char(string="Name")

class ConcessionCode(models.Model):
	_name = 'concession.code'

	name= fields.Char(string="Name")




class AccountTax(models.Model):
	_inherit = 'account.tax'

	@api.constrains('consession_from')
	def _code_constrains(self):
		if self.consession_from > self.consession_to:
			raise ValidationError(_("'Concession Start Date' must be before ' Concession To Date'"))


	pan_no_in = fields.Boolean(string="Non PAN %")
	tds_active = fields.Boolean(string="Active TDS")
	tds_group_id = fields.Many2one('account.tds', string="TDS Group")
	account_tds_section_id = fields.Many2one('account.tds.section', string="TDS Section")
	tds_nature_id = fields.Many2one('tds.nature.deduction', string="TDS Nature Of Deduction")
	assessee_code_id = fields.Many2one('assessee.code', string="Assessee Code")
	concession_code_id = fields.Many2one('concession.code', string="Concession Code")
	consession_from = fields.Date(string='Concession From Date', default=fields.Datetime.now)
	consession_to = fields.Date(string='Concession To Date', default=fields.Datetime.now)
	

class ResPartner(models.Model):
	_inherit = 'res.partner'
	
	pan_no = fields.Char(string="PAN No",size=10)
	tds_account_lines = fields.One2many('tax.deduction.source','res_partner_id' ,string="Tax")



# class PurchaseOrderLine(models.Model):
# 	_inherit = 'purchase.order.line'

# 	apply_tds = fields.Boolean(string="TDS")

# 	@api.onchange('apply_tds')
# 	def onchange_tds_id(self):
# 		tds_ids=[]
# 		for each in self.order_id.partner_id.tds_account_lines:
# 			if each.tax_id:
# 				tds_ids.append(each.tax_id.id)
# 		# pdb.set_trace()
# 		if self.product_id.supplier_taxes_id:
# 			for each_tax in self.product_id.supplier_taxes_id:
# 				tds_ids.append(each_tax.id)


# 		self.taxes_id= [(6, 0, tds_ids)]


class AccountMoveLine(models.Model):
	_inherit = 'account.move.line'

	apply_tds = fields.Boolean(string="TDS")

	@api.onchange('apply_tds')
	def onchange_tds_id(self):
		tds_ids=[]
		# pdb.set_trace()
		for each in self.move_id.partner_id.tds_account_lines:
			if each.tax_id:
				tds_ids.append(each.tax_id.id)
		if self.product_id.supplier_taxes_id:
			for each_tax in self.product_id.supplier_taxes_id:
				tds_ids.append(each_tax.id)

		self.tax_ids= [(6, 0, tds_ids)]




class TaxDeductionSource(models.Model):
	_name = 'tax.deduction.source'
	
	res_partner_id = fields.Many2one('res.partner', string="Partner")
	tax_id = fields.Many2one('account.tax', string="TDS")
	pan_tds_in = fields.Boolean(string="Non PAN %", readonly=True) 
	concession_tds_code_id = fields.Many2one('concession.code', string="Concession Code")
	amount= fields.Integer("Amount", readonly=True)

	# @api.onchange('tax_id')
	# def onchange_tax_id(self):
	# 	for line in self.tax_id:
	# 		self.create({
	# 		'amount': line.amount,
	# 		'concession_tds_code_id': line.concession_code_id.id if line.concession_code_id.id else 0,
	# 		'pan_tds_in':line.pan_no_in
	# 		})

	@api.onchange('tax_id')
	def onchange_tax_id(self):
		for line in self.tax_id:
			self.amount= line.amount
			concession_tds_code_id= line.concession_code_id.id if line.concession_code_id.id else 0
			self.pan_tds_in=line.pan_no_in
			

	@api.constrains('tax_id')
	def _code_constrains(self):
		if not self.res_partner_id.pan_no:
			raise ValidationError(_("'The Pan Number and TDS Rates are Mismatched'"))
	