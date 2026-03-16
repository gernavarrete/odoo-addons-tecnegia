from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    cashier_console_cashbox_name = fields.Char(string="Cashbox name")
    cashier_console_payment_method_ids = fields.Many2many(
        comodel_name="account.journal",
        relation="company_cashier_console_payment_rel",
        column1="company_id",
        column2="journal_id",
        string="Cashier payment methods",
        domain="[('type', 'in', ('cash', 'bank'))]",
    )
    cashier_console_cash_rounding_method_id = fields.Many2one(
        "account.cash.rounding",
        string="Cash rounding",
        help="Rounding method applied to cashier cash payments.",
    )
    cashier_console_login_as_employee = fields.Boolean(string="Login as employee")
    cashier_console_allow_employee_switch = fields.Boolean(string="Allow employee switch")
    cashier_console_basic_permissions = fields.Selection(
        selection=[
            ("restricted", "Basic permissions"),
            ("standard", "Standard permissions"),
        ],
        default="standard",
        string="Basic level",
    )
    cashier_console_advanced_permissions = fields.Selection(
        selection=[
            ("none", "No advanced permissions"),
            ("full", "Advanced permissions"),
        ],
        default="none",
        string="Advanced permissions",
    )
    cashier_console_default_tax_id = fields.Many2one("account.tax", string="Default sales tax")
    cashier_console_temp_account_id = fields.Many2one("account.account", string="Default temporary account")
    cashier_console_default_order_journal_id = fields.Many2one(
        "account.journal",
        string="Default order journal",
        domain="[('type', '=', 'sale')]",
    )
    cashier_console_default_invoice_journal_id = fields.Many2one(
        "account.journal",
        string="Default invoice journal",
        domain="[('type', '=', 'sale')]",
    )
    cashier_console_auto_invoice = fields.Boolean(string="Auto invoice")
    cashier_console_print_portal_info = fields.Boolean(
        string="Print portal info on receipts",
        help="Include the portal URL on printed receipts.",
    )
    cashier_console_send_receipt_whatsapp = fields.Boolean(string="Send receipts via WhatsApp")
    cashier_console_foreign_currency_journal_id = fields.Many2one(
        "account.journal",
        string="Foreign currency collection journal",
        domain="[('type', 'in', ('cash', 'bank'))]",
    )
    cashier_console_local_currency_journal_id = fields.Many2one(
        "account.journal",
        string="Local currency collection journal",
        domain="[('type', 'in', ('cash', 'bank'))]",
    )
