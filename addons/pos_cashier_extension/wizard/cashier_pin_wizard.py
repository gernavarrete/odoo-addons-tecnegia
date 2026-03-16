from odoo import _, fields, models
from odoo.exceptions import AccessDenied, UserError


class CashierPinWizard(models.TransientModel):
    _name = "cashier.pin.wizard"
    _description = "Cashier PIN Verification"

    session_id = fields.Many2one("cashier.console.session", required=True)
    operation = fields.Selection(
        [("open", "Open Session"), ("close", "Close Session")],
        required=True,
    )
    pin = fields.Char(string="PIN", required=True)

    def action_verify_pin(self):
        self.ensure_one()
        user = self.env.user

        # 1. Buscar el empleado asociado al usuario actual
        employee = self.env["hr.employee"].search([("user_id", "=", user.id)], limit=1)

        # Si el usuario no tiene un empleado vinculado, no podemos validar por PIN de empleado
        if not employee:
            # Opcional: Si eres Admin (ID 2) o Superuser (ID 1) podrías dejar pasar sin PIN
            if user.id in (1, 2):
                return self._continue_operation()

            raise UserError(
                _(
                    "Este usuario no tiene un empleado asociado. Configure el empleado en la ficha del usuario."
                )
            )

        # 2. Verificar que el empleado tenga PIN configurado
        if not employee.pin:
            raise UserError(
                _("El empleado %s no tiene un NIP/PIN configurado.") % employee.name
            )

        # 3. Comparar el PIN ingresado con el del empleado
        if employee.pin != self.pin:
            raise AccessDenied(_("PIN incorrecto."))

        # 4. Si todo es correcto, procedemos
        return self._continue_operation()

    def _continue_operation(self):
        """Ejecuta la operación original una vez validado el PIN"""
        if self.operation == "open":
            return self.session_id.with_context(
                pin_validated=True
            ).action_open_session()
        elif self.operation == "close":
            return self.session_id.with_context(
                pin_validated=True
            ).action_close_session()
