from odoo.exceptions import UserError
from odoo import api, fields, models, _
from num2words import num2words
import pdb

class taxorder(models.Model):
	_inherit = 'account.move'

	po_no=fields.Char(string="PO No")

	def amount_words(self, amount):
		amount=str(amount)
		amt_words = amount.split(".")
		
		return  num2words(int(amt_words[0]),lang='en_IN').title() + ' ' + ' Rupees Only '