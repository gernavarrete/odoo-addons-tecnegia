# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date


class CustomerPaymentTracking(models.Model):
    """
    Modelo para rastrear pagos de clientes y su impacto en el límite de crédito.
    Permite diferenciar entre pagos inmediatos (efectivo/transferencia) y pagos
    diferidos (cheques) que se liberan al depositarse o usarse para pagar proveedores.
    """
    _name = 'customer.payment.tracking'
    _description = 'Rastreo de Pagos para Límite de Crédito'
    _order = 'create_date desc'
    _rec_name = 'display_name'

    # --- Información del Pago ---
    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True,
        ondelete='cascade',
        index=True,
    )
    payment_id = fields.Many2one(
        'account.payment',
        string='Pago',
        ondelete='cascade',
        index=True,
    )
    check_id = fields.Many2one(
        'l10n_latam.check',
        string='Cheque',
        ondelete='set null',
        index=True,
    )
    move_id = fields.Many2one(
        'account.move',
        string='Factura/Nota de Débito',
        ondelete='set null',
        help='Factura o Nota de Débito relacionada al movimiento de crédito',
    )

    # --- Montos ---
    amount = fields.Monetary(
        string='Monto',
        required=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        default=lambda self: self.env.company.currency_id,
    )

    # --- Tipo y Estado ---
    tracking_type = fields.Selection([
        ('payment_cash', 'Pago en Efectivo'),
        ('payment_transfer', 'Pago por Transferencia'),
        ('payment_check', 'Pago con Cheque'),
        ('check_cleared', 'Cheque Liberado'),
        ('check_rejected', 'Cheque Rechazado'),
        ('rejection_fee', 'Gastos por Rechazo'),
    ], string='Tipo', required=True, default='payment_cash')

    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('cleared', 'Liberado'),
        ('rejected', 'Rechazado'),
    ], string='Estado', default='pending', required=True)

    # --- Fechas ---
    payment_date = fields.Date(
        string='Fecha de Pago',
        default=fields.Date.context_today,
    )
    clearing_date = fields.Date(
        string='Fecha de Liberación',
        help='Fecha en que el pago fue efectivamente liberado (para cheques)',
    )

    # --- Campos Computed ---
    display_name = fields.Char(
        string='Nombre',
        compute='_compute_display_name',
        store=True,
    )
    is_credit_consuming = fields.Boolean(
        string='Consume Crédito',
        compute='_compute_is_credit_consuming',
        store=True,
        help='Indica si este registro está consumiendo crédito del cliente (aún no liberado)',
    )

    # --- Notas ---
    notes = fields.Text(string='Notas')

    @api.depends('tracking_type', 'payment_id', 'check_id', 'amount')
    def _compute_display_name(self):
        type_labels = dict(self._fields['tracking_type'].selection)
        for record in self:
            type_label = type_labels.get(record.tracking_type, '')
            ref = ''
            if record.check_id:
                ref = record.check_id.name or ''
            elif record.payment_id:
                ref = record.payment_id.name or ''
            record.display_name = f"{type_label} - {ref} (${record.amount:,.2f})"

    @api.depends('tracking_type', 'state')
    def _compute_is_credit_consuming(self):
        """
        Determina si este registro está consumiendo crédito:
        - Pagos en efectivo/transferencia: NO consumen (liberan inmediatamente)
        - Pagos con cheque pendiente: SÍ consumen (hasta que se libere)
        - Cheques liberados: NO consumen
        - Cheques rechazados: SÍ consumen (vuelven a la deuda)
        - Gastos por rechazo: SÍ consumen (se suman a la deuda)
        """
        for record in self:
            if record.tracking_type in ('payment_cash', 'payment_transfer', 'check_cleared'):
                record.is_credit_consuming = False
            elif record.tracking_type in ('check_rejected', 'rejection_fee'):
                record.is_credit_consuming = True
            elif record.tracking_type == 'payment_check':
                # Cheque pendiente consume crédito hasta que se libere
                record.is_credit_consuming = (record.state == 'pending')
            else:
                record.is_credit_consuming = False

    # --- Métodos de Negocio ---

    def action_clear_check(self, clearing_reason='deposited'):
        """
        Marca un cheque como liberado y actualiza el crédito del cliente.

        Args:
            clearing_reason: 'deposited' o 'vendor_payment'
        """
        for record in self:
            if record.tracking_type != 'payment_check':
                continue
            if record.state != 'pending':
                continue

            record.write({
                'state': 'cleared',
                'clearing_date': fields.Date.context_today(self),
                'notes': (record.notes or '') + f"\nLiberado por: {clearing_reason} - {fields.Datetime.now()}",
            })

            # Crear registro de liberación
            self.create({
                'partner_id': record.partner_id.id,
                'payment_id': record.payment_id.id,
                'check_id': record.check_id.id,
                'amount': record.amount,
                'currency_id': record.currency_id.id,
                'tracking_type': 'check_cleared',
                'state': 'cleared',
                'clearing_date': fields.Date.context_today(self),
                'notes': f"Cheque liberado por: {clearing_reason}",
            })

            # Recalcular crédito del cliente
            if record.partner_id:
                record.partner_id._compute_credit_used()

    def action_reject_check(self, rejection_fee=0.0, rejection_reason=''):
        """
        Marca un cheque como rechazado, revierte la liberación de crédito,
        y opcionalmente agrega gastos por rechazo.

        Args:
            rejection_fee: Monto de gastos por rechazo
            rejection_reason: Motivo del rechazo
        """
        for record in self:
            if record.tracking_type != 'payment_check':
                continue

            # Actualizar estado del registro original
            record.write({
                'state': 'rejected',
                'notes': (record.notes or '') + f"\nRechazado: {rejection_reason} - {fields.Datetime.now()}",
            })

            # Crear registro de rechazo (esto vuelve a consumir crédito)
            self.create({
                'partner_id': record.partner_id.id,
                'payment_id': record.payment_id.id,
                'check_id': record.check_id.id,
                'amount': record.amount,
                'currency_id': record.currency_id.id,
                'tracking_type': 'check_rejected',
                'state': 'rejected',
                'notes': f"Motivo: {rejection_reason}",
            })

            # Si hay gastos por rechazo, crear registro adicional
            if rejection_fee > 0:
                self.create({
                    'partner_id': record.partner_id.id,
                    'payment_id': record.payment_id.id,
                    'check_id': record.check_id.id,
                    'amount': rejection_fee,
                    'currency_id': record.currency_id.id,
                    'tracking_type': 'rejection_fee',
                    'state': 'rejected',
                    'notes': f"Gastos por rechazo de cheque",
                })

            # Recalcular crédito del cliente
            if record.partner_id:
                record.partner_id._compute_credit_used()

    @api.model
    def create_from_payment(self, payment):
        """
        Crea un registro de tracking desde un pago confirmado.
        Analiza el método de pago para determinar el tipo de tracking.

        Returns:
            customer.payment.tracking record
        """
        if not payment or payment.payment_type != 'inbound':
            return self.env['customer.payment.tracking']

        if not payment.partner_id or not payment.partner_id.current_account_custom:
            return self.env['customer.payment.tracking']

        # Determinar tipo de pago
        method_code = payment.payment_method_line_id.code if payment.payment_method_line_id else ''

        # Detectar si es cheque
        is_check = (
            method_code in ('third_party_check', 'new_third_party_checks', 'in_third_party_checks') or
            getattr(payment, 'l10n_latam_move_check_ids', False) or
            getattr(payment, 'l10n_latam_new_check_ids', False)
        )

        # Detectar si es transferencia
        is_transfer = method_code in ('electronic', 'batch_payment', 'manual')

        if is_check:
            tracking_type = 'payment_check'
            state = 'pending'
            # Obtener el cheque si existe
            checks = getattr(payment, 'l10n_latam_new_check_ids', False) or getattr(payment, 'l10n_latam_move_check_ids', False)
            check_id = checks[0].id if checks else False
        elif is_transfer:
            tracking_type = 'payment_transfer'
            state = 'cleared'
            check_id = False
        else:
            # Efectivo u otro método inmediato
            tracking_type = 'payment_cash'
            state = 'cleared'
            check_id = False

        vals = {
            'partner_id': payment.partner_id.id,
            'payment_id': payment.id,
            'check_id': check_id,
            'amount': payment.amount,
            'currency_id': payment.currency_id.id,
            'tracking_type': tracking_type,
            'state': state,
            'payment_date': payment.date,
            'clearing_date': payment.date if state == 'cleared' else False,
        }

        return self.create(vals)
