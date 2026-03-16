from odoo import models, fields, api, _
from markupsafe import Markup 

class CreditAccountChange(models.TransientModel):
    _name = "credit.account.change"
    _description = "Credit Account Change Wizard"

    partner_id = fields.Many2one(
        "res.partner", string="Customer", required=True, readonly=True
    )
    currency_id = fields.Many2one(related="partner_id.currency_id")

    action_type = fields.Selection(
        [("open", "Open Account"), ("close", "Close Account")],
        string="Action",
        required=True,
        readonly=True,
    )

    # Campo informativo para ver el límite actual
    current_credit_limit = fields.Monetary(
        string="Current Approved Limit",
        related="partner_id.credit_limit_custom",
        readonly=True,
        currency_field="currency_id",
    )

    # Aquí el usuario pone el NUEVO TOTAL deseado
    amount = fields.Monetary(
        string="New Requested Total Limit",
        currency_field="currency_id",
        help="Enter the FINAL total amount desired (Current + Increase).",
    )

    reason = fields.Char(
        string="Main Reason",
        required=True,
        help="E.g. Customer request, Payment default, etc.",
    )
    description = fields.Text(string="Additional Details")
    is_open_already = fields.Boolean(related="partner_id.current_account_custom")

    def action_confirm(self):
        """Executes the state change and logs the reason in the chatter."""
        self.ensure_one()

        new_state = True if self.action_type == "open" else False

        vals = {"current_account_custom": new_state}

        # Guardamos el monto en 'requested' sin tocar el 'approved' todavía
        if new_state and self.amount > 0:
            vals["requested_credit_limit"] = self.amount
            # Forzamos estado 'requested' para iniciar flujo si se pidió monto
            vals["credit_limit_state"] = "requested"

            # Disparar la notificación al analista automáticamente
            self.partner_id.action_request_credit_limit(from_wizard=True)

        # Aplicamos cambios (sudo para evitar bloqueo de permisos si lo hace un vendedor)
        self.partner_id.sudo().write(vals)

        # Si cambió el estado a requested, disparar notificaciones desde el partner
        if new_state and self.amount > 0:
            self.partner_id.action_request_credit_limit(from_wizard=True)

        # Log en Chatter usando Markup para que se vea el HTML
        user = self.env.user.name
        action_str = _("OPEN") if new_state else _("CLOSE")
        
        # Construimos el encabezado
        header_text = _("%s requested to %s the Credit Account.") % (user, action_str)

        # Usamos Markup y %s para insertar los valores de forma segura pero manteniendo el HTML
        body = Markup("<b>%s</b>") % header_text
        body += Markup("<ul>")
        body += Markup("<li><b>%s:</b> %s</li>") % (_('Reason'), self.reason)

        if new_state and self.amount > 0:
            formatted_amount = self.currency_id.format(self.amount)
            body += Markup("<li><b>%s:</b> %s</li>") % (_('New Requested Total'), formatted_amount)

        if self.description:
            body += Markup("<li><b>%s:</b> %s</li>") % (_('Details'), self.description)
        
        body += Markup("</ul>")

        self.partner_id.message_post(body=body, message_type="comment")

        return {"type": "ir.actions.act_window_close"}