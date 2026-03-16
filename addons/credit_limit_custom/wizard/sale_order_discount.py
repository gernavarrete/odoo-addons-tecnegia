from odoo import models, api, _
from odoo.exceptions import UserError

class SaleOrderDiscount(models.TransientModel):
    _inherit = "sale.order.discount"

    def _create_discount_lines(self):
        """
        Extendemos el método nativo para agregar la validación del límite
        antes de crear las líneas.
        """
        # 1. VALIDACIÓN: Calcular porcentaje y verificar límite
        self.ensure_one()

        current_percentage = 0.0

        if self.discount_type == 'so_discount':
            # En tipo porcentaje, el valor viene directo (ej. 0.10 para 10%)
            current_percentage = self.discount_percentage * 100.0

        elif self.discount_type == 'amount':
            # En tipo monto fijo, calculamos qué porcentaje representa sobre el total
            so_amount = self.sale_order_id.amount_total
            if so_amount:
                # Lógica para restar impuestos fijos del total (adaptada a Odoo 19 con tax_ids)
                fixed_taxes_amount = 0
                for line in self.sale_order_id.order_line:
                    # CORRECCIÓN: Usamos tax_ids (nuevo estándar Odoo 19)
                    taxes = line.tax_ids.flatten_taxes_hierarchy()
                    for tax in taxes.filtered(lambda t: t.amount_type == "fixed"):
                        fixed_taxes_amount += tax.amount * line.product_uom_qty

                adjusted_total = so_amount - fixed_taxes_amount
                if adjusted_total > 0:
                    current_percentage = (self.discount_amount / adjusted_total) * 100.0

        # Verificar el límite configurado en la compañía
        limit = self.company_id.limit_discount
        has_manager_group = self.env.user.has_group("credit_limit_custom.group_discount_limit_manager")

        if current_percentage > limit and not has_manager_group:
             raise UserError(
                _("You cannot add a discount greater than the established limit, which is: %s%%", limit)
            )

        # 2. EJECUCIÓN: Llamar al método original de Odoo
        # Esto usará la lógica nativa nueva (_prepare_global_discount_so_lines)
        # y evitará el error de 'AttributeError'.
        return super()._create_discount_lines()
