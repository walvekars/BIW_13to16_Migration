# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import calendar
from datetime import timedelta
from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import calendar
from xlwt import easyxf
from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError,Warning
import xlwt
import io
import base64
import datetime
import math


class TdsRegister(models.TransientModel):
    _name = "tds.register.report"
    _description = "Tds Register Report"

    date_start = fields.Date(string="Start Date", required=True, default=fields.Date.today)
    date_end = fields.Date(string="End Date", required=True, default=fields.Date.today)
    tds_report = fields.Binary('TDS Report')
    file_name = fields.Char('File Name')
    tds_report_printed = fields.Boolean('TDS Report Printed')

    @api.constrains('date_start')
    def _code_constrains(self):
        if self.date_start > self.date_end:
            raise ValidationError(_("'Start Date' must be before 'End Date'"))

    def get_summary(self):
        self.ensure_one()

        if self.date_start:

            workbook = xlwt.Workbook()
            amount_tot = 0
            column_heading_style = easyxf('font:height 210;font:bold True;align: horiz center;')
            value_heading_style = easyxf('font:height 210;font:bold True;align: horiz right;')
            worksheet = workbook.add_sheet('Tds Register', cell_overwrite_ok=True)
            right_alignment= easyxf('font:height 200; align: horiz right;')
            center_alignment= easyxf('font:height 200; align: horiz center;')
            left_alignment= easyxf('font:height 200; align: horiz left;')
            current_company_name = self.env.user.company_id.name
            report_heading = " TDS Report" + ' ' + datetime.datetime.strftime(self.date_start, '%d-%m-%Y')  + ' '+ 'To' + ' '+ datetime.datetime.strftime(self.date_end, '%d-%m-%Y') 
            worksheet.write_merge(1, 1, 4, 8, current_company_name, easyxf('font:height 250;font:bold True;align: horiz center;'))
            worksheet.write_merge(2, 2, 4, 8, report_heading, easyxf('font:height 250;font:bold True;align: horiz center;'))
            worksheet.write(3, 0, _('SL NO'), column_heading_style)
            worksheet.write(3, 1, _('POSTING DATE'), column_heading_style)
            worksheet.write(3, 2, _('VENDOR BILL NO.'), column_heading_style)
            worksheet.write(3, 3, _('VENDOR REF'), column_heading_style)
            worksheet.write(3, 4, _('PARTY CODE'), column_heading_style)
            worksheet.write(3, 5, _('VENDOR NAME'), column_heading_style)
            worksheet.write(3, 6, _('Product Name'), column_heading_style)
            worksheet.write(3, 7, _('Product Code'), column_heading_style)
            worksheet.write(3, 8, _('ANALYTIC ACCOUNT'), column_heading_style)
            worksheet.write(3, 9, _('ACCOUNT'), column_heading_style)
            worksheet.write(3, 10, _('DEDUCTEE PAN NO.'), column_heading_style)
            worksheet.write(3, 11, _('ASSESSEE CODE'), column_heading_style)
            worksheet.write(3, 12, _('TDS SEC'), column_heading_style)
            worksheet.write(3, 13, _('Nature'), column_heading_style)
            worksheet.write(3, 14, _('Qty'), column_heading_style)
            worksheet.write(3, 15, _('Unit Price'), column_heading_style)
            worksheet.write(3, 16, _('Base Amount'), column_heading_style)
            worksheet.write(3, 17, _('TDS %'), column_heading_style)
            worksheet.write(3, 18, _('TDS AMOUNT'), column_heading_style)

            worksheet.col(1).width = 4500
            worksheet.col(2).width = 4500
            worksheet.col(3).width = 4500
            worksheet.col(4).width = 4500
            worksheet.col(5).width = 4500
            worksheet.col(6).width = 4800
            worksheet.col(7).width = 4500
            worksheet.col(8).width = 4500
            worksheet.col(9).width = 4500
            worksheet.col(10).width = 4500
            worksheet.col(11).width = 4500
            worksheet.col(12).width = 4500
            worksheet.col(13).width = 4500
            worksheet.col(28).width = 4500
            worksheet.row(1).height = 300
            worksheet.row(2).height = 300
            
            row = 4
            s_no=1
            for rec in self:
                tot_sgst = tot_cgst = tot_gst = tot_amount = tot_cogs_amount = tot_with_tax_amount = tot_gp_amount =  0.0
                val_rec = self.env['account.move'].search([('type','=','in_invoice'),('state','=','posted'),('date','>=',rec.date_start),('date','<=',rec.date_end)])
                if val_rec:
                    tot_base_amount=tot_tds =0.0
                    for invoice in val_rec:
                        for invoice_line in invoice.invoice_line_ids:
                            
                            for each_line in invoice_line.tax_ids:
                                if each_line.tds_active== True:
                                    igst_rate  = each_line.amount if each_line.amount else ' '
                                    sub_total_amount = round(invoice_line.quantity*invoice_line.price_unit,2)
                                    worksheet.write(row, 0, s_no, center_alignment)
                                    worksheet.write(row, 1, datetime.datetime.strftime(invoice.date, '%d-%m-%Y'), left_alignment)
                                    worksheet.write(row, 2, invoice.name)
                                    worksheet.write(row, 3, invoice.ref, center_alignment)
                                    worksheet.write(row, 4, invoice.partner_id.ref)
                                    worksheet.write(row, 5, invoice.partner_id.name)
                                    worksheet.write(row, 6, invoice_line.product_id.name)
                                    worksheet.write(row, 7, invoice_line.product_id.default_code)
                                    worksheet.write(row, 8, invoice_line.analytic_account_id.name)
                                    worksheet.write(row, 9, invoice_line.account_id.name)
                                    worksheet.write(row, 10, invoice.partner_id.pan_no)
                                    worksheet.write(row, 11, each_line.assessee_code_id.name)
                                    worksheet.write(row, 12, each_line.account_tds_section_id.name)
                                    worksheet.write(row, 13, each_line.tds_nature_id.name)
                                    worksheet.write(row, 14, invoice_line.quantity, right_alignment)
                                    worksheet.write(row, 15, invoice_line.price_unit, right_alignment)
                                    worksheet.write(row, 16, sub_total_amount, right_alignment)
                                    worksheet.write(row, 17, -(each_line.amount), right_alignment)
                                    worksheet.write(row, 18, (sub_total_amount)*-(each_line.amount)/100, right_alignment)
                                    tot_base_amount += sub_total_amount
                                    tot_tds += (sub_total_amount)*-(each_line.amount)/100
                                    
                                    s_no += 1
                                    row += 1
                    worksheet.write(row, 16, tot_base_amount, value_heading_style)
                    worksheet.write(row, 18, tot_tds, value_heading_style) 
                       

            fp = io.BytesIO()
            workbook.save(fp)
            excel_file = base64.encodestring(fp.getvalue())
            self.tds_report = excel_file
            self.file_name = 'TDS Report.xls'
            self.tds_report_printed = True
            fp.close()

            return {
            'view_mode': 'form',
            'res_id': self.id,
            'res_model': 'tds.register.report',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'context': self.env.context,
            'target': 'new',
                       }