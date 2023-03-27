
from lxml import etree
from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountAccount(models.Model):
    _inherit = 'account.account'

    z_cost_center_bool = fields.Boolean(string="Dimension",default=False)
