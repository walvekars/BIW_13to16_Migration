# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime

class BiCompanyCustom(models.Model):
	_inherit='res.company'

	lut_number=fields.Char(string='LUT NO-ARN No')
	display_date=fields.Date(string='Date',default=datetime.today())
