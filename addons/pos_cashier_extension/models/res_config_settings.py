from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    cashier_config_ids = fields.One2many(
        "cashier.config",
        string="Configured Cashier Boxes",
        related="company_id.cashier_config_ids",  # Necesitarás añadir este campo en res.company
        readonly=False,
    )

    cashier_console_cashbox_name = fields.Char(
        related="company_id.cashier_console_cashbox_name", readonly=False
    )
    cashier_console_payment_method_ids = fields.Many2many(
        related="company_id.cashier_console_payment_method_ids",
        string="Payment methods",
        readonly=False,
    )
    cashier_console_cash_rounding_method_id = fields.Many2one(
        related="company_id.cashier_console_cash_rounding_method_id",
        readonly=False,
    )
    cashier_console_login_as_employee = fields.Boolean(
        related="company_id.cashier_console_login_as_employee", readonly=False
    )
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
    cashier_console_auto_invoice = fields.Boolean(
        related="company_id.cashier_console_auto_invoice", readonly=False
    )
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

    def action_open_cashier_boxes(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Cashier Boxes",
            "res_model": "cashier.config",
            "view_mode": "tree,form",
            "target": "current",
        }
