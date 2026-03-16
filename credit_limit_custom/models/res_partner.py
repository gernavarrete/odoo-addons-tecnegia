from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, AccessError


class ResPartner(models.Model):
    _inherit = "res.partner"

    # --- STATUS FIELDS ---
    credit_limit_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("requested", "Requested"),
            ("analyzed", "Analyzed"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Credit Status",
        default="draft",
        tracking=True,
    )

    # MODIFICADO: Eliminado readonly=True para permitir edición condicional en la vista
    requested_credit_limit = fields.Monetary(
        string="Requested Credit Limit",
        currency_field="currency_id",
        tracking=True,
        # readonly=True,  <-- Comentado para permitir edición por Aprobador/Analista
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        index=True,
    )

    current_account_custom = fields.Boolean(
        string="Credit Account",
        tracking=True,
        help="Allows processing credit orders or checks the limit validation.",
    )

    credit_limit_custom = fields.Monetary(
        string="Approved Credit Limit",
        currency_field="currency_id",
        tracking=True,
        readonly=True,
    )

    # --- COMPUTED FIELDS ---
    credit_limit_total_custom = fields.Monetary(
        string="Total Credit Limit",
        currency_field="currency_id",
        copy=False,
        compute="_compute_credit_limit_total",
        store=True,
        readonly=True,
    )

    credit_used = fields.Monetary(
        string="Credit Used",
        currency_field="currency_id",
        compute="_compute_credit_used",
        store=True,
        readonly=True,
    )

    available_credit = fields.Monetary(
        string="Available Credit",
        currency_field="currency_id",
        compute="_compute_available_credit",
        store=True,
        readonly=True,
    )

    can_request_credit = fields.Boolean(compute="_compute_can_request", store=False)
    can_approve_credit = fields.Boolean(compute="_compute_can_request", store=False)
    has_permission_to_change = fields.Boolean(
        string="Has Permission to Change",
        compute="_compute_has_permission_to_change",
        store=False,
    )

    analyst_approval_enabled = fields.Boolean(
        string="Analyst Approval Enabled",
        compute="_compute_analyst_approval_enabled",
        store=False,
    )

    # Campo para control del bloqueo por analista
    account_blocked_by_analyst = fields.Boolean(
        string="Account Blocked by Analyst",
        default=False,
        tracking=True,
        help="Indicates if the account was blocked due to non-payment or risk.",
    )

    # Campo auxiliar para identificar al analista en la vista
    can_edit_limit_analyst = fields.Boolean(
        compute="_compute_can_request",
        store=False,
        string="Can Edit Limit (Analyst)"
    )

    # Relación con registros de tracking de pagos
    payment_tracking_ids = fields.One2many(
        'customer.payment.tracking',
        'partner_id',
        string='Historial de Pagos para Crédito',
    )

    # Campo computed para cheques pendientes de liberación
    pending_check_amount = fields.Monetary(
        string='Monto en Cheques Pendientes',
        currency_field='currency_id',
        compute='_compute_pending_check_amount',
        store=False,  # No almacenar, busca directamente en l10n_latam.check
        help='Monto total de cheques recibidos que aún no han sido depositados o utilizados',
    )

    # --- ACCIONES DE BLOQUEO (ANALISTA) ---
    def action_analyst_block_account(self):
        """Bloquea la cuenta y marca el flag de bloqueo por analista."""
        self.ensure_one()
        if not self.env.user.has_group("credit_limit_custom.group_credit_risk_analyst"):
            raise AccessError(
                _("Only the Credit Risk Analyst can perform this action.")
            )

        self.write(
            {"current_account_custom": False, "account_blocked_by_analyst": True}
        )
        self.message_post(body=_("⛔ Account BLOCKED by Analyst (Payment Pending)."))

    def action_analyst_unblock_account(self):
        """Reapertura de cuenta: Restaura el estado activo sin borrar el límite."""
        self.ensure_one()
        if not self.env.user.has_group("credit_limit_custom.group_credit_risk_analyst"):
            raise AccessError(
                _("Only the Credit Risk Analyst can perform this action.")
            )

        self.write(
            {"current_account_custom": True, "account_blocked_by_analyst": False}
        )
        self.message_post(body=_("✅ Account RE-OPENED by Analyst. Credit restored."))

    # --- CALCULATION LOGIC ---
    @api.depends(
        "invoice_ids.amount_residual",
        "invoice_ids.state",
        "invoice_ids.move_type",
        "invoice_ids.payment_state",
        "sale_order_ids.amount_total",
        "sale_order_ids.state",
        "sale_order_ids.invoice_ids.state",
        "sale_order_ids.payment_term_id.skip_credit_limit",
        "payment_tracking_ids.is_credit_consuming",
        "payment_tracking_ids.amount",
        "payment_tracking_ids.state",
    )
    def _compute_credit_used(self):
        for partner in self:
            # 1. Facturas impagas (residuo)
            unpaid_invoices = partner.invoice_ids.filtered(
                lambda inv: inv.move_type == "out_invoice"
                and inv.state == "posted"
                and inv.payment_state in ["not_paid", "partial"]
            )
            total_invoices = sum(unpaid_invoices.mapped("amount_residual"))

            # 2. Créditos impagas (residuo) - esto resta
            unpaid_refunds = partner.invoice_ids.filtered(
                lambda inv: inv.move_type == "out_refund"
                and inv.state == "posted"
                and inv.payment_state in ["not_paid", "partial"]
            )
            total_refunds = sum(unpaid_refunds.mapped("amount_residual"))

            # 3. Órdenes confirmadas no facturadas (SOLO A CRÉDITO)
            # Las órdenes de CONTADO (skip_credit_limit=True) NO consumen crédito
            # porque se pagan en el momento (POS)
            confirmed_orders = partner.sale_order_ids.filtered(
                lambda so: so.state in ["sale", "done"]
                and not so.payment_term_id.skip_credit_limit  # Excluir contado
            )

            total_orders_risk = 0.0
            for order in confirmed_orders:
                posted_invoices = order.invoice_ids.filtered(
                    lambda x: x.state == "posted" and x.move_type == "out_invoice"
                )
                invoiced_amount = sum(posted_invoices.mapped("amount_total"))
                pending = order.amount_total - invoiced_amount
                if pending > 0:
                    total_orders_risk += pending

            # 4. Cheques pendientes de liberación (consumen crédito)
            # Busca directamente en l10n_latam.check los cheques que:
            # - Fueron recibidos de este cliente (original_customer_id)
            # - No han sido liberados aún (is_check_cleared = False)
            pending_checks = self.env['l10n_latam.check'].search([
                ('original_customer_id', '=', partner.id),
                ('is_check_cleared', '=', False),
            ])
            pending_check_total = sum(pending_checks.mapped('amount'))

            # 5. Cheques rechazados + gastos (vuelven a consumir crédito)
            rejected_tracking = partner.payment_tracking_ids.filtered(
                lambda t: t.tracking_type in ('check_rejected', 'rejection_fee')
            )
            rejected_total = sum(rejected_tracking.mapped('amount'))

            # CÁLCULO FINAL:
            # Crédito usado = Facturas - Créditos + Órdenes a crédito + Cheques pendientes + Rechazados
            # NOTA: Órdenes de CONTADO NO se incluyen porque se pagan en POS
            partner.credit_used = (
                (total_invoices - total_refunds) +
                total_orders_risk +
                pending_check_total +
                rejected_total
            )



    def _compute_pending_check_amount(self):
        """Calcula el monto total de cheques pendientes de liberación.

        Busca directamente en l10n_latam.check los cheques que:
        - Fueron recibidos de este cliente (original_customer_id)
        - No han sido liberados aún (is_check_cleared = False)
        """
        Check = self.env['l10n_latam.check']
        for partner in self:
            # Buscar cheques no liberados de este cliente
            pending_checks = Check.search([
                ('original_customer_id', '=', partner.id),
                ('is_check_cleared', '=', False),
            ])
            partner.pending_check_amount = sum(pending_checks.mapped('amount'))


    @api.depends("credit_limit_total_custom", "credit_used")
    def _compute_available_credit(self):
        for partner in self:
            partner.available_credit = (
                partner.credit_limit_total_custom - partner.credit_used
            )

    def _check_credit_limit(self, amount):
        self.ensure_one()
        if not self.current_account_custom:
            return True
        available = self.available_credit
        if amount > available:
            raise ValidationError(
                _(
                    "This invoice/order would exceed the available credit limit.\n"
                    "Credit Limit: %s\n"
                    "Credit Used: %s\n"
                    "Available: %s\n"
                    "Amount Attempted: %s"
                )
                % (
                    self.currency_id.format(self.credit_limit_total_custom),
                    self.currency_id.format(self.credit_used),
                    self.currency_id.format(available),
                    self.currency_id.format(amount),
                )
            )
        return True

    @api.depends("credit_limit_custom")
    def _compute_credit_limit_total(self):
        for record in self:
            record.credit_limit_total_custom = record.credit_limit_custom

    @api.constrains("credit_limit_custom")
    def _check_credit_limit_values(self):
        for record in self:
            if record.credit_limit_custom < 0:
                raise models.ValidationError(_("Credit limits cannot be negative"))

    @api.depends_context("uid")
    def _compute_has_permission_to_change(self):
        for rec in self:
            rec.has_permission_to_change = self.env.user.has_group(
                "credit_limit_custom.group_discount_limit_manager"
            )

    def _compute_analyst_approval_enabled(self):
        """Returns True if the company setting allows analyst approval AND the user is analyst."""
        is_analyst = self.env.user.has_group("credit_limit_custom.group_credit_risk_analyst")
        company_allows = self.env.company.analyst_can_approve_credit
        for rec in self:
            rec.analyst_approval_enabled = is_analyst and company_allows

    def _is_analyst_allowed_to_approve(self):
        """Helper: checks if the current user is an analyst with delegated approval."""
        return (
            self.env.company.analyst_can_approve_credit
            and self.env.user.has_group("credit_limit_custom.group_credit_risk_analyst")
        )

    @api.depends_context("uid")
    def _compute_can_request(self):
        for rec in self:
            rec.can_request_credit = self.env.user.has_group(
                "credit_limit_custom.group_credit_limit_applicant"
            )

            # El Analista puede aprobar SOLO si la compañía lo permite
            rec.can_approve_credit = self.env.user.has_group(
                "credit_limit_custom.group_credit_limit_approver"
            ) or rec._is_analyst_allowed_to_approve()

            # Check exclusivo de analista
            rec.can_edit_limit_analyst = self.env.user.has_group(
                "credit_limit_custom.group_credit_risk_analyst"
            )

    # --- WORKFLOW LOGIC ---

    def _get_users_from_group(self, group_xml_id):
        """Busca usuarios pertenecientes a un grupo de forma segura (Compatible Odoo 19)."""
        group = self.env.ref(group_xml_id, raise_if_not_found=False)
        if not group:
            return self.env["res.users"]

        # CORRECCIÓN ODOO 19:
        # El campo 'users' fue renombrado a 'user_ids' en el modelo res.groups.
        users = group.sudo().user_ids

        # Filtro Multi-Compañía:
        # Solo notificamos a usuarios que tengan acceso a la compañía actual.
        current_company = self.env.company
        users = users.filtered(lambda u: current_company in u.company_ids)

        return users

    def _schedule_activity_for_group(self, group_xml_id, summary, note):
        """Crea una actividad para cada usuario del grupo especificado."""
        users = self._get_users_from_group(group_xml_id)
        if not users:
            return

        activity_type_id = self.env.ref("mail.mail_activity_data_todo").id
        for user in users:
            # Evitamos duplicar si ya tiene la actividad
            existing = self.activity_ids.filtered(
                lambda a: a.user_id == user and a.summary == summary
            )
            if not existing:
                self.activity_schedule(
                    activity_type_id=activity_type_id,
                    summary=summary,
                    note=note,
                    user_id=user.id,
                )

    def _feedback_activities(self):
        self.activity_ids.filtered(
            lambda a: a.activity_type_id == self.env.ref("mail.mail_activity_data_todo")
        ).action_feedback(feedback=_("Stage completed or rejected."))

    # --- MAIN ACTION: REQUEST CREDIT ---
    def action_request_credit_limit(self, from_wizard=False):
        """
        Starts the request workflow.
        from_wizard: Indicates if called from the wizard (skip permission check to avoid double check).
        """
        if not from_wizard and not self.env.user.has_group(
            "credit_limit_custom.group_credit_limit_applicant"
        ):
            raise AccessError(_("You do not have permission to request."))

        for partner in self:
            # Allow request if draft or previously rejected (retry)
            if partner.credit_limit_state in [
                "draft",
                "rejected",
                "approved",
                "requested",
            ]:

                # LOGIC CHANGE: Do NOT reset credit_limit_custom to 0.0.
                # Keep the old limit active until the new one is approved.

                # If account was closed, open it.
                if not partner.current_account_custom:
                    partner.sudo().current_account_custom = True

            partner.credit_limit_state = "requested"

            # 1. Notify Analyst (Activity + Message)
            partner._notify_risk_analyst()
            partner._schedule_activity_for_group(
                "credit_limit_custom.group_credit_risk_analyst",
                _("Analyze Risk"),
                _("Request for %s")
                % partner.currency_id.format(partner.requested_credit_limit),
            )

            # 2. Notify Approver (Message Only)
            partner._notify_approver_only_message()

    def _notify_risk_analyst(self):
        """Notifica al Analista de Riesgo (Actividad + Email)."""
        group_xml_id = "credit_limit_custom.group_credit_risk_analyst"
        users = self._get_users_from_group(group_xml_id)

        # 1. Crear Actividad
        self._schedule_activity_for_group(
            group_xml_id,
            _("Analyze Risk"),
            _("Request for %s") % self.currency_id.format(self.requested_credit_limit),
        )

        # 2. Enviar Mensaje al Muro (Chatter) etiquetando a los usuarios
        if users:
            self.message_post(
                subject=_("Credit Limit Request"),
                body=_("User %s requests a credit limit increase to %s.")
                % (
                    self.env.user.name,
                    self.currency_id.format(self.requested_credit_limit),
                ),
                subtype_xmlid="mail.mt_note",
                partner_ids=users.partner_id.ids,  # Esto asegura que les llegue notificación
            )

    def _notify_approver_only_message(self):
        """Solo envía mensaje informativo al Aprobador (sin actividad)."""
        group_xml_id = "credit_limit_custom.group_credit_limit_approver"
        users = self._get_users_from_group(group_xml_id)

        if users:
            self.message_post(
                subject=_("New Request (Information)"),
                body=_("A new credit limit request of %s is pending analysis.")
                % self.currency_id.format(self.requested_credit_limit),
                subtype_xmlid="mail.mt_note",
                partner_ids=users.partner_id.ids,
            )

    def action_analyze_credit_limit(self):
        self.ensure_one()
        if not self.env.user.has_group("credit_limit_custom.group_credit_risk_analyst"):
            raise AccessError(_("Only Risk Analyst."))
        if self.credit_limit_state == "requested":
            self.credit_limit_state = "analyzed"
            self._feedback_activities()
            self._schedule_activity_for_group(
                "credit_limit_custom.group_credit_limit_approver",
                _("Approve Limit"),
                _("Analysis completed for %s") % self.name,
            )
            self.message_post(body=_("Analysis completed."))

    def action_approve_credit_limit(self):
        self.ensure_one()
        if not self.env.user.has_group("credit_limit_custom.group_credit_limit_approver") and \
           not self._is_analyst_allowed_to_approve():
            raise AccessError(_("Only the Approver can perform this action."))

        if self.credit_limit_state in ["requested", "analyzed"]:
            # HERE is where we replace the limit
            self.credit_limit_custom = self.requested_credit_limit
            self.credit_limit_state = "approved"
            self._feedback_activities()
            self.message_post(body=_("Approved by %s.") % self.env.user.name)

    def action_reject_credit_limit(self):
        self.ensure_one()
        if not self.env.user.has_group("credit_limit_custom.group_credit_limit_approver") and \
           not self._is_analyst_allowed_to_approve():
            raise AccessError(_("Only the Approver can perform this action."))

        if self.credit_limit_state in ["requested", "analyzed"]:
            self.credit_limit_state = "rejected"
            # We keep the OLD limit active if rejected,
            # or we can set it to 0 only if the account is closed.
            # For now, let's assume rejection means "Keep things as they were"
            # or "No new limit granted".

            # If it was a new request (limit was 0), we might want to keep it 0.
            # If it was an increase, we revert requested to 0 but keep approved as is.
            self.requested_credit_limit = 0.0

            # DO NOT reset credit_limit_custom to 0 unless you want to block the client completely on rejection.
            # self.credit_limit_custom = 0.0

            self._feedback_activities()
            self.message_post(body=_("Rejected by %s.") % self.env.user.name)

    # --- WRITE FIX ---
    def write(self, vals):
        if "credit_limit_custom" in vals:
            if not self.env.is_superuser() and \
               not self.env.user.has_group("credit_limit_custom.group_credit_limit_approver") and \
               not self._is_analyst_allowed_to_approve():
                raise AccessError(
                    _(
                        "Only the Approving Administrator can modify the 'Approved Credit Limit' field."
                    )
                )

            for rec in self:
                if rec.credit_limit_custom != vals["credit_limit_custom"]:
                    rec.message_post(
                        body=_("Limit modified by %s.") % self.env.user.name
                    )

        if "current_account_custom" in vals:
            for rec in self:
                if rec.current_account_custom != vals["current_account_custom"]:
                    action = (
                        "activated" if vals["current_account_custom"] else "deactivated"
                    )
                    rec.message_post(
                        body=_("Credit Account check %s by %s.")
                        % (action, self.env.user.name)
                    )
        return super().write(vals)

    def action_open_account_change_wizard(self):
        self.ensure_one()
        next_action = "close" if self.current_account_custom else "open"
        return {
            "name": _("Credit Account Management"),
            "type": "ir.actions.act_window",
            "res_model": "credit.account.change",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_partner_id": self.id,
                "default_action_type": next_action,
            },
        }

    def action_update_credit_limit_wizard(self):
        """Abre el wizard en modo 'open' para permitir actualizar el monto."""
        self.ensure_one()
        return {
            "name": _("Actualizar Límite de Crédito"),
            "type": "ir.actions.act_window",
            "res_model": "credit.account.change",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_partner_id": self.id,
                "default_action_type": "open",
            },
        }


# --- REINTEGRATED MISSING MODELS ---
class AccountMove(models.Model):
    _inherit = "account.move"

    credit_limit_total_custom = fields.Monetary(
        related="partner_id.credit_limit_total_custom"
    )
    credit_used = fields.Monetary(related="partner_id.credit_used")
    available_credit = fields.Monetary(related="partner_id.available_credit")
    current_account_custom = fields.Boolean(related="partner_id.current_account_custom")

    def _post(self, soft=True):
        res = super()._post(soft=soft)
        for move in self:
            if move.move_type == "out_invoice" and move.partner_id:
                move.partner_id._compute_credit_used()
        return res


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def action_post(self):
        res = super().action_post()
        for payment in self:
            # Caso 1: Pago recibido de un cliente
            if payment.partner_type == "customer" and payment.partner_id:
                # Crear registro de tracking si el cliente tiene cuenta corriente activa
                if payment.partner_id.current_account_custom:
                    self.env['customer.payment.tracking'].create_from_payment(payment)
                # Recalcular crédito del cliente
                payment.partner_id._compute_credit_used()

            # Caso 2: Pago a proveedor con cheques de terceros
            # Cuando se usa un cheque de terceros para pagar a un proveedor,
            # debemos liberar el crédito del cliente original del cheque
            if payment.partner_type == "supplier" and payment.payment_type == "outbound":
                # Buscar cheques de terceros usados en este pago
                # Los cheques están vinculados como operaciones
                Check = self.env['l10n_latam.check']
                checks_used = Check.search([
                    ('operation_ids', 'in', [payment.id])
                ])

                for check in checks_used:
                    if check.original_customer_id and check.original_customer_id.current_account_custom:
                        # El cheque fue liberado - actualizar crédito del cliente original
                        customer = check.original_customer_id
                        customer._compute_credit_used()

                        # Notificar en el chatter del cliente
                        customer.message_post(
                            body=_(
                                "✅ Cheque Nº %s ($%s) usado para pagar a %s. Crédito disponible: $%s"
                            ) % (
                                check.name or '',
                                '{:,.2f}'.format(check.amount),
                                payment.partner_id.name,
                                '{:,.2f}'.format(customer.available_credit)
                            ),
                            subtype_xmlid='mail.mt_note',
                        )
        return res

