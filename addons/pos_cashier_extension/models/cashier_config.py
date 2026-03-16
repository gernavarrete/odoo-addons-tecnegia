from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CashierConfig(models.Model):
    _name = "cashier.config"
    _description = "Cashier Console Configuration"

    name = fields.Char(
        string="Cashier Box Name",
        required=True,
        help="Name of the Cashier Console box.",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Sales Journal",
        domain="[('type', '=', 'sale')]",
        help="Sales Journal for recording transactions.",
        required=True,
    )
    cash_journal_id = fields.Many2one(
        "account.journal",
        string="Cash Journal",
        domain="[('type', '=', 'cash')]",
        help="Cash Journal for managing cash movements.",
        required=True,
    )
    # Otros campos de configuración que puedas necesitar
    # Por ejemplo, para los ajustes de pago, redondeo, etc.
    # login_as_employee = fields.Boolean(string="Login as Employee", default=True) # Si lo necesitas
    # allow_employee_switch = fields.Boolean(string="Allow Employee Switch", default=True) # Si lo necesitas

    _sql_constraints = [
        (
            "name_uniq",
            "unique(name, company_id)",
            "The name of the cashier console must be unique per company!",
        ),
    ]
