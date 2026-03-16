from odoo import models, fields, api, _


class ResCompany(models.Model):

    _inherit = "res.company"

    limit_line_discount = fields.Float("Sales Line Discount Limit")
    limit_discount = fields.Float("Sales Discount Limit")
    analyst_can_approve_credit = fields.Boolean(
        "Allow Risk Analyst to Approve/Reject Credit",
        default=False,
        help="If enabled, users with the Credit Risk Analyst role can also approve or reject credit limit requests.",
    )
