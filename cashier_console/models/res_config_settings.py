from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    cashier_console_cashbox_name = fields.Char(related="company_id.cashier_console_cashbox_name", readonly=False)
    cashier_console_payment_method_ids = fields.Many2many(
        related="company_id.cashier_console_payment_method_ids",
        string="Payment methods",
        readonly=False,
    )
    cashier_console_cash_rounding_method_id = fields.Many2one(
        related="company_id.cashier_console_cash_rounding_method_id",
        readonly=False,
    )
    cashier_console_login_as_employee = fields.Boolean(related="company_id.cashier_console_login_as_employee", readonly=False)
    cashier_console_allow_employee_switch = fields.Boolean(
        related="company_id.cashier_console_allow_employee_switch",
        readonly=False,
    )
    cashier_console_basic_permissions = fields.Selection(
        related="company_id.cashier_console_basic_permissions",
        readonly=False,
    )
    cashier_console_advanced_permissions = fields.Selection(
        related="company_id.cashier_console_advanced_permissions",
        readonly=False,
    )
    cashier_console_default_tax_id = fields.Many2one(
        related="company_id.cashier_console_default_tax_id",
        readonly=False,
    )
    cashier_console_temp_account_id = fields.Many2one(
        related="company_id.cashier_console_temp_account_id",
        readonly=False,
    )
    cashier_console_default_order_journal_id = fields.Many2one(
        related="company_id.cashier_console_default_order_journal_id",
        readonly=False,
    )
    cashier_console_default_invoice_journal_id = fields.Many2one(
        related="company_id.cashier_console_default_invoice_journal_id",
        readonly=False,
    )
    cashier_console_auto_invoice = fields.Boolean(related="company_id.cashier_console_auto_invoice", readonly=False)
    cashier_console_print_portal_info = fields.Boolean(
        related="company_id.cashier_console_print_portal_info",
        readonly=False,
    )
    cashier_console_send_receipt_whatsapp = fields.Boolean(
        related="company_id.cashier_console_send_receipt_whatsapp",
        readonly=False,
    )
    cashier_console_foreign_currency_journal_id = fields.Many2one(
        related="company_id.cashier_console_foreign_currency_journal_id",
        readonly=False,
    )
    cashier_console_local_currency_journal_id = fields.Many2one(
        related="company_id.cashier_console_local_currency_journal_id",
        readonly=False,
    )
