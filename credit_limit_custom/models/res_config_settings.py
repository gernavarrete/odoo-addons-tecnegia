from odoo import models, fields, api, _
from odoo.api import readonly


class ResConfigSettings(models.TransientModel):

    _inherit = "res.config.settings"

    limit_line_discount = fields.Float(
        "Sales Line Discount Limit",
        related="company_id.limit_line_discount",
        readonly=False,
    )
    limit_discount = fields.Float(
        "Sales Discount Limit", related="company_id.limit_discount", readonly=False
    )
    analyst_can_approve_credit = fields.Boolean(
        "Allow Risk Analyst to Approve/Reject Credit",
        related="company_id.analyst_can_approve_credit",
        readonly=False,
    )
