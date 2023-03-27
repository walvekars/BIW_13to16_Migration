from odoo import models,fields

class report_account_general_ledger_costNew(models.AbstractModel):
    _name = "account.general.ledger.cost"


class report_account_aged_partner_inherit(models.AbstractModel):
    _name = "account.aged.partner"
    _description = "Aged Partner Balances"
    _inherit = 'account.report'

    filter_date = {'date': '', 'filter': 'today'}
    filter_unfold_all = False