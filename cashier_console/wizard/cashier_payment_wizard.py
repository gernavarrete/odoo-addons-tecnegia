from odoo import _, fields, models


class CashierPaymentWizard(models.TransientModel):
    _name = "cashier.payment.wizard"
    _description = "Cashier Console payment wizard"

    session_id = fields.Many2one("cashier.console.session", string="Session", required=True)
    order_id = fields.Many2one("sale.order", string="Sales Order", required=True)
    amount = fields.Monetary(
        string="Amount to collect",
        currency_field="currency_id",
        required=True,
    )
    currency_id = fields.Many2one(related="order_id.currency_id", store=False)
    journal_id = fields.Many2one(
        "account.journal",
        string="Payment method",
        domain="[('type', 'in', ('cash', 'bank'))]",
        required=True,
    )
    communication = fields.Char(string="Receipt reference")

    def _prepare_invoice_values(self):
        self.ensure_one()
        self.order_id._compute_invoice_status()
        if self.order_id.invoice_status == "invoiced":
            return self.order_id.invoice_ids[:1]
        invoice = self.order_id._create_invoices()
        invoice.action_post()
        return invoice[:1]

    def action_confirm(self):
        self.ensure_one()
        invoice = self._prepare_invoice_values()
        register_payments = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=invoice.ids)
            .create(
                {
                    "journal_id": self.journal_id.id,
                    "amount": self.amount,
                    "communication": self.communication or invoice.name,
                }
            )
        )
        register_payments.action_create_payments()
        self.session_id.message_post(
            body=_("A payment of %s was registered for %s")
            % (self.amount, self.order_id.name)
        )
        action = invoice.action_view_invoice()
        action["target"] = "current"
        return action
