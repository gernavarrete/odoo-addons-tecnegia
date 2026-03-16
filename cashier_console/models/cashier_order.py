from odoo import _, api, fields, models


class CashierConsoleOrder(models.Model):
    _name = "cashier.console.order"
    _description = "Cashier Console order tracking"
    _order = "create_date desc"

    name = fields.Char(string="Reference", compute="_compute_name", store=True)
    session_id = fields.Many2one(
        "cashier.console.session",
        string="Session",
        required=True,
        default=lambda self: self.env.context.get("default_session_id"),
    )
    sale_order_id = fields.Many2one("sale.order", string="Sales Order", required=True)
    invoice_id = fields.Many2one(
        "account.move",
        string="Invoice",
        domain=[("move_type", "=", "out_invoice")],
    )
    company_id = fields.Many2one(related="sale_order_id.company_id", store=True)
    partner_id = fields.Many2one(related="sale_order_id.partner_id", store=True)
    amount_total = fields.Monetary(
        string="Total",
        currency_field="currency_id",
        related="sale_order_id.amount_total",
        store=True,
    )
    currency_id = fields.Many2one(related="sale_order_id.currency_id", store=True)
    state = fields.Selection(
        selection=[
            ("to_invoice", "To invoice"),
            ("invoiced", "Invoiced"),
        ],
        compute="_compute_state",
        store=True,
    )

    @api.depends("sale_order_id.name")
    def _compute_name(self):
        for record in self:
            record.name = record.sale_order_id.name

    @api.depends("invoice_id", "invoice_id.payment_state", "sale_order_id.invoice_status")
    def _compute_state(self):
        for record in self:
            if record.invoice_id and record.invoice_id.payment_state in ("paid", "in_payment"):
                record.state = "invoiced"
            elif record.sale_order_id.invoice_status == "invoiced":
                record.state = "invoiced"
            else:
                record.state = "to_invoice"

    def action_open_sale_order(self):
        self.ensure_one()
        return {
            "name": self.sale_order_id.name,
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "view_mode": "form",
            "res_id": self.sale_order_id.id,
            "target": "current",
        }

    def action_open_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            return self.action_register_payment()
        return {
            "name": self.invoice_id.name,
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": self.invoice_id.id,
            "target": "current",
        }

    def action_register_payment(self):
        self.ensure_one()
        return {
            "name": _("Register payment"),
            "type": "ir.actions.act_window",
            "res_model": "cashier.payment.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_order_id": self.sale_order_id.id,
                "default_session_id": self.session_id.id,
            },
        }
