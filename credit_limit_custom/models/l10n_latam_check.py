# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class L10nLatamCheck(models.Model):
    """
    Extensión del modelo de cheques para detectar cuándo un cheque ha sido
    "liberado" (depositado o usado para pagar a un proveedor) y actualizar
    el crédito disponible del cliente correspondiente.
    """
    _inherit = 'l10n_latam.check'

    # --- Campos Computed ---
    is_check_cleared = fields.Boolean(
        string='Cheque Liberado',
        compute='_compute_is_check_cleared',
        store=True,
        help='Indica si el cheque fue depositado o usado para pagar a un proveedor',
    )

    original_customer_id = fields.Many2one(
        'res.partner',
        string='Cliente Original',
        compute='_compute_original_customer',
        store=True,
        help='Cliente que entregó este cheque como pago',
    )

    @api.depends('payment_id', 'payment_id.partner_id', 'payment_id.partner_type')
    def _compute_original_customer(self):
        """Identifica el cliente original que entregó el cheque."""
        for check in self:
            if check.payment_id and check.payment_id.partner_type == 'customer':
                check.original_customer_id = check.payment_id.partner_id
            else:
                check.original_customer_id = False

    @api.depends(
        'current_journal_id',
        'operation_ids',
        'operation_ids.state',
        'operation_ids.payment_type',
        'operation_ids.partner_type',
    )
    def _compute_is_check_cleared(self):
        """
        Un cheque se considera "liberado" cuando:
        1. NO tiene current_journal_id (ya salió de la empresa)
        2. O fue usado para pagar a un proveedor (operación outbound a supplier)

        Las transferencias internas entre diarios (outbound customer) NO liberan el cheque.
        """
        for check in self:
            cleared = False

            # Criterio 1: El cheque ya no está en ningún diario de la empresa
            if not check.current_journal_id:
                cleared = True
            else:
                # Criterio 2: Fue usado para pagar a un proveedor
                supplier_payment = check.operation_ids.filtered(
                    lambda op: op.state in ('posted', 'paid')
                    and op.payment_type == 'outbound'
                    and op.partner_type == 'supplier'
                )
                if supplier_payment:
                    cleared = True

            check.is_check_cleared = cleared


    def write(self, vals):
        """Override write para detectar cambios en estado de liberación."""
        # Evitar recursión: si ya estamos en proceso de recálculo, no volver a hacerlo
        if self.env.context.get('skip_check_cleared_recompute'):
            return super().write(vals)

        # Guardar estado anterior
        old_cleared_states = {check.id: check.is_check_cleared for check in self}

        result = super().write(vals)

        # Solo verificar cambios si se modificaron campos relevantes
        relevant_fields = {'current_journal_id', 'operation_ids'}
        if not relevant_fields & set(vals.keys()):
            return result

        # Verificar si algún cheque cambió su estado de liberación
        for check in self.with_context(skip_check_cleared_recompute=True):
            old_cleared = old_cleared_states.get(check.id, False)
            new_cleared = check.is_check_cleared

            if not old_cleared and new_cleared:
                # El cheque acaba de ser liberado
                check._on_check_cleared()

        return result

    def _on_check_cleared(self):
        """
        Callback cuando un cheque es liberado.
        Actualiza el crédito del cliente original.
        """
        self.ensure_one()

        if not self.original_customer_id:
            return

        customer = self.original_customer_id
        if not customer.current_account_custom:
            return

        # Determinar razón de liberación
        last_op = self.operation_ids.filtered(
            lambda op: op.state in ('posted', 'paid') and op.payment_type == 'outbound'
        ).sorted(key=lambda p: (p.date, p.id), reverse=True)

        if last_op and last_op[0].partner_type == 'supplier':
            clearing_reason = 'vendor_payment'
            reason_text = 'Pago a proveedor'
        else:
            clearing_reason = 'deposited'
            reason_text = 'Depositado'

        # Buscar el registro de tracking correspondiente a este cheque (si existe)
        tracking = self.env['customer.payment.tracking'].search([
            ('partner_id', '=', customer.id),
            ('check_id', '=', self.id),
            ('tracking_type', '=', 'payment_check'),
            ('state', '=', 'pending'),
        ], limit=1)

        if tracking:
            # Liberar el crédito vía tracking
            tracking.action_clear_check(clearing_reason=clearing_reason)

        # SIEMPRE forzar recálculo del crédito utilizado del cliente
        # Esto es necesario porque credit_used se calcula con search() no con depends
        customer._compute_credit_used()

        # Notificar en el chatter del cliente
        customer.message_post(
            body=_(
                "✅ Cheque Nº %s ($%s) liberado (%s). Crédito disponible: $%s"
            ) % (
                self.name or '',
                '{:,.2f}'.format(self.amount),
                reason_text,
                '{:,.2f}'.format(customer.available_credit)
            ),
            subtype_xmlid='mail.mt_note',
        )

    @api.model
    def create(self, vals):
        """Override create para vincular cheques nuevos con tracking."""
        record = super().create(vals)
        # El tracking se crea desde AccountPayment.action_post
        return record
