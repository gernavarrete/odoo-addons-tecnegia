from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class CashierConsoleSession(models.Model):
    _name = "cashier.console.session"
    _description = "Cashier Console session"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Reference", default="New", tracking=True)
    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        tracking=True,
        string="Employee",
    )
    user_id = fields.Many2one(related="employee_id.user_id", string="User", store=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(related="company_id.currency_id", store=True)
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("open", "Open"),
            ("close", "Closed"),
        ],
        default="draft",
        tracking=True,
    )
    opening_amount = fields.Monetary(
        string="Opening amount", currency_field="currency_id"
    )
    closing_amount = fields.Monetary(
        string="Closing amount", currency_field="currency_id"
    )
    order_ids = fields.One2many("cashier.console.order", "session_id", string="Orders")
    to_invoice_count = fields.Integer(compute="_compute_order_stats")
    invoiced_count = fields.Integer(compute="_compute_order_stats")

    @api.depends("order_ids.state")
    def _compute_order_stats(self):
        for session in self:
            session.to_invoice_count = len(
                session.order_ids.filtered(lambda o: o.state == "to_invoice")
            )
            session.invoiced_count = len(
                session.order_ids.filtered(lambda o: o.state == "invoiced")
            )

    def action_open_session(self):
        self.ensure_one()
        # 1. Verificar Permiso de Grupo
        if not self.env.user.has_group(
            "pos_cashier_extension.group_cashier_console_user"
        ):
            raise AccessError(
                _("You don't have the permissions to open a cashier session.")
            )

        # 2. Lógica de PIN
        # Si el usuario tiene PIN configurado Y no venimos de validarlo exitosamente:
        if self.env.user.pos_security_pin and not self.env.context.get("pin_validated"):
            return {
                "name": _("Enter PIN"),
                "type": "ir.actions.act_window",
                "res_model": "cashier.pin.wizard",
                "view_mode": "form",
                "target": "new",
                "context": {"default_session_id": self.id, "default_operation": "open"},
            }

        # 3. Lógica Original (Apertura)
        if self.state != "draft":
            raise UserError(_("Only draft sessions can be opened."))
        self.write({"state": "open"})

    def action_close_session(self):
        self.ensure_one()
        # 1. Verificar Permiso de Grupo
        if not self.env.user.has_group(
            "pos_cashier_extension.group_cashier_console_user"
        ):
            raise AccessError(
                _("You don't have the permissions to close a cashier session.")
            )

        # 2. Lógica de PIN
        if self.env.user.pos_security_pin and not self.env.context.get("pin_validated"):
            return {
                "name": _("Enter PIN"),
                "type": "ir.actions.act_window",
                "res_model": "cashier.pin.wizard",
                "view_mode": "form",
                "target": "new",
                "context": {
                    "default_session_id": self.id,
                    "default_operation": "close",
                },
            }

        # 3. Lógica Original (Cierre)
        if self.state != "open":
            raise UserError(_("Only open sessions can be closed."))

        # Calcular cierre (si tenías lógica aquí, mantenla)
        self.write(
            {
                "state": "close",
                "closing_amount": self.opening_amount
                + sum(self.order_ids.mapped("amount_total")),
            }
        )

    def action_view_orders(self):
        self.ensure_one()
        return {
            "name": _("Cashier orders"),
            "type": "ir.actions.act_window",
            "res_model": "cashier.console.order",
            "view_mode": "tree,form",
            "domain": [["session_id", "=", self.id]],
            "context": {"default_session_id": self.id},
        }
