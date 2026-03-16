from odoo import models, fields, _, api
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    partner_credit_limit = fields.Monetary(
        string="Total Credit Limit",
        currency_field="currency_id",
        compute="_compute_partner_credit_info",
        readonly=True,
        help="Total credit limit assigned to the customer.",
    )

    partner_credit_used = fields.Monetary(
        string="Credit Used",
        currency_field="currency_id",
        compute="_compute_partner_credit_info",
        readonly=True,
        help="Amount of credit already used by the customer.",
    )

    partner_available_credit = fields.Monetary(
        string="Available Credit",
        currency_field="currency_id",
        compute="_compute_partner_credit_info",
        readonly=True,
        help="Current available credit for the customer.",
    )

    @api.depends("partner_id")
    def _compute_partner_credit_info(self):
        """Compute partner credit information."""
        for order in self:
            partner = order.partner_id
            if not partner:
                order.partner_credit_limit = 0.0
                order.partner_available_credit = 0.0
                order.partner_credit_used = 0.0
            else:
                order.partner_credit_limit = (
                    getattr(partner, "credit_limit_custom", 0.0)
                    or getattr(partner, "credit_limit_total_custom", 0.0)
                    or getattr(partner, "credit_limit", 0.0)
                )

                order.partner_available_credit = getattr(
                    partner, "available_credit", 0.0
                )
                order.partner_credit_used = getattr(partner, "credit_used", 0.0)

    def action_confirm(self):
        """
        Overrides order confirmation to validate credit limit before confirming.
        """
        for order in self:
            # 1. If the payment term has the "Skip validation" flag, it is 'Cash'.
            # Skip check and proceed with confirmation.
            if order.payment_term_id and order.payment_term_id.skip_credit_limit:
                continue

            # 2. If it is NOT 'Cash', it is 'Credit'. Validate.
            partner = order.partner_id

            # 2a. Validate if the customer has the Credit Account enabled
            if not partner.current_account_custom:
                raise UserError(
                    _(
                        "Confirmation Denied:\n\n"
                        "Customer '%s' does not have the Credit Account enabled.",
                        partner.name,
                    )
                )

            # 2b. Validate if the order total exceeds the available credit
            if order.amount_total > partner.available_credit:

                # Call the .format() method directly from the currency object
                available_credit_str = partner.currency_id.format(
                    partner.available_credit
                )
                order_total_str = order.currency_id.format(order.amount_total)

                raise UserError(
                    _(
                        "Confirmation Denied:\n\n"
                        "The order (%(order_total)s) exceeds the available credit limit for customer '%(partner_name)s'.\n\n"
                        "Available Credit: %(available_credit)s\n\n"
                        "Contact the responsible person.",
                        order_total=order_total_str,
                        partner_name=partner.name,
                        available_credit=available_credit_str,
                    )
                )

        # 3. If all orders pass validation, confirm.
        return super(SaleOrder, self).action_confirm()
