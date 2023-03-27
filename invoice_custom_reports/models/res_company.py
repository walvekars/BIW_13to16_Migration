# -*- coding: utf-8 -*-

from odoo import api, models, fields, _


class Company(models.Model):
    _inherit = 'res.company'

    state_code = fields.Char()

class Partner(models.Model):
    _inherit = 'res.partner'

    attn = fields.Char(string='Attn')
