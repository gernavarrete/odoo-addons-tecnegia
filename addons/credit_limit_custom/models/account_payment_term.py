from odoo import api, fields, models, _


class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"

    skip_credit_limit = fields.Boolean(string="Skip Credit Limit Validation")
