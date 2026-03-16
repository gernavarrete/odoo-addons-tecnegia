from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrderLine(models.Model):

    _inherit = "sale.order.line"

    @api.constrains("discount")
    def _check_discount_limit(self):
        for rec in self:
            if (
                rec.discount > rec.company_id.limit_line_discount
                and not rec.env.user.has_group(
                    "credit_limit_custom.group_discount_limit_manager"
                )
            ):
                raise UserError(
                    _(
                        "You cannot add a discount greater than the established limit, which is: %s",
                        rec.company_id.limit_line_discount,
                    )
                )
