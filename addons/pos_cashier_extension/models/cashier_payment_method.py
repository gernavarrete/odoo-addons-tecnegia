# -*- coding: utf-8 -*-
"""
Cashier payment methods.

This model replicates the behaviour of `pos.payment.method` but is
used by the Cashier Console / Cashier Boxes instead of Point of Sale.
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CashierPaymentMethod(models.Model):
    """Payment methods available in the Cashier Console.

    Each method is linked to an accounting journal and can be assigned
    to one or more cashier boxes.
    """

    _name = "cashier.payment.method"
    _description = "Cashier Payment Method"
    _order = "sequence, name"
    _check_company_auto = True

    name = fields.Char(
        string="Method",
        required=True,
        translate=True,
    )
    active = fields.Boolean(
        default=True,
        help="Uncheck to hide the payment method without deleting it.",
    )
    sequence = fields.Integer(
        default=10,
        help="Defines the display order.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Journal",
        required=True,
        domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]",
        help="Accounting journal used to register payments for this method.",
    )
    is_cash_count = fields.Boolean(
        string="Cash",
        help=(
            "Enable this if this method is part of the cash counting at closing.\n"
            "Disable it for non-cash methods such as cards or bank transfers."
        ),
    )
    cashier_config_ids = fields.Many2many(
        comodel_name="cashier.config",
        relation="cashier_config_payment_method_rel",
        column1="payment_method_id",
        column2="cashier_config_id",
        string="Cashier Boxes",
        help="Cashier boxes where this payment method is available.",
    )

    _sql_constraints = [
        (
            "name_company_uniq",
            "unique(name, company_id)",
            "The payment method name must be unique per company.",
        ),
    ]

    @api.constrains("journal_id", "company_id")
    def _check_journal_company(self):
        """Ensure journal company matches payment method company."""
        for method in self:
            if (
                method.journal_id
                and method.journal_id.company_id
                and method.journal_id.company_id != method.company_id
            ):
                raise ValidationError(
                    _(
                        "The company of the journal must match the company of the "
                        "cashier payment method."
                    )
                )
