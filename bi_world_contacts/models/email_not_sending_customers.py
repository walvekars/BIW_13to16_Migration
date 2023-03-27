from odoo.exceptions import UserError
from odoo import api, fields, models, _
from num2words import num2words
import pdb


class EmailNotSending(models.Model):
    _name = "res.email"

    partner_id = fields.Many2one('res.partner', string="Customer")

