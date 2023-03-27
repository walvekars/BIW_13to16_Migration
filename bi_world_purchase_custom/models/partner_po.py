from odoo.exceptions import UserError, ValidationError, MissingError
from odoo import api, fields, models, _
from num2words import num2words
import pdb


class Contacts(models.Model):
    _inherit = 'res.partner'

    res_po = fields.One2many('res.purchase.order', 'partner_id', string="Purchase Order")
    vies_failed_message = fields.Char()



