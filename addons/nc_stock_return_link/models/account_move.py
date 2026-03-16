# account_nc_stock_return_link/models/account_move.py
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    is_return_nc_locked = fields.Boolean(
        string="NC Locked by Return",
        help="Indicates if quantities are locked due to associated returns",
        compute="_compute_is_return_nc_locked",
        store=False,
    )

    def _compute_is_return_nc_locked(self):
        """Compute if the Credit Note is locked based on its lines"""
        for move in self:
            if move.move_type == "out_refund" and move.invoice_line_ids:
                move.is_return_nc_locked = any(
                    line.is_return_nc_locked
                    for line in move.invoice_line_ids
                    if not line.display_type
                )
            else:
                move.is_return_nc_locked = False

    def _get_returned_qty_by_invoice_line(self, invoice):
        """Return a dict {invoice_line_id: returned_qty}"""
        self.ensure_one()
        res = {}

        _logger.info(
            "🔍 SEARCHING RETURNS for invoice: %s (ID: %s)", invoice.name, invoice.id
        )

        if not invoice or invoice.move_type != "out_invoice":
            _logger.info("❌ Not a valid customer invoice")
            return res

        # Get all sale order lines from the invoice
        all_sols = invoice.invoice_line_ids.mapped("sale_line_ids")
        _logger.info("📋 Sale lines found: %s - IDs: %s", len(all_sols), all_sols.ids)

        if not all_sols:
            _logger.info("❌ No associated sale lines")
            return res

        # Find validated outgoing moves (deliveries)
        out_moves = self.env["stock.move"].search(
            [
                ("sale_line_id", "in", all_sols.ids),
                ("state", "=", "done"),
                ("picking_type_id.code", "=", "outgoing"),
            ]
        )

        _logger.info(
            "🚚 Outgoing moves found: %s - IDs: %s", len(out_moves), out_moves.ids
        )
        for m in out_moves:
            _logger.info(
                "   📦 Outgoing ID: %s, Product: %s, Qty: %s, SOL: %s",
                m.id,
                m.product_id.display_name,
                m.product_uom_qty,
                m.sale_line_id.id,
            )

        if not out_moves:
            _logger.info("❌ No validated outgoing moves")
            return res

        # Find return moves that reference the out_moves
        return_moves = self.env["stock.move"].search(
            [
                ("origin_returned_move_id", "in", out_moves.ids),
                ("state", "=", "done"),
                ("picking_type_id.code", "=", "incoming"),
            ]
        )

        _logger.info("🔄 Return moves found: %s", len(return_moves))
        for rm in return_moves:
            _logger.info(
                "   📦 Return ID: %s, Product: %s, Qty: %s, Origin: %s, Origin SOL: %s",
                rm.id,
                rm.product_id.display_name,
                rm.product_uom_qty,
                rm.origin_returned_move_id.id,
                rm.origin_returned_move_id.sale_line_id.id,
            )

        # Create mapping of returned quantities by invoice line
        _logger.info("📝 Processing %s invoice lines", len(invoice.invoice_line_ids))

        for inv_line in invoice.invoice_line_ids:
            _logger.info(
                "🔍 Invoice line ID: %s, Product: %s, Display Type: %s, SOLs: %s",
                inv_line.id,
                inv_line.product_id.display_name if inv_line.product_id else "None",
                inv_line.display_type,
                inv_line.sale_line_ids.ids,
            )

            # Skip display lines (sections, notes)
            if inv_line.display_type in ("line_section", "line_note"):
                _logger.info(
                    "   ⏩ Skipping display line: %s (type: %s)",
                    inv_line.id,
                    inv_line.display_type,
                )
                continue

            _logger.info(
                "📝 Processing product line: %s, Product: %s",
                inv_line.id,
                inv_line.product_id.display_name,
            )

            total_returned = 0.0

            # For each sale line associated with this invoice line
            for sol in inv_line.sale_line_ids:
                _logger.info(
                    "   🔍 Checking sale line: %s, Product: %s",
                    sol.id,
                    sol.product_id.display_name,
                )

                # Find return moves for this sale line and product
                sol_return_moves = return_moves.filtered(
                    lambda rm: rm.origin_returned_move_id.sale_line_id.id == sol.id
                )

                _logger.info(
                    "   📦 Return moves for SOL %s: %s", sol.id, len(sol_return_moves)
                )

                # Filter by specific product of the invoice line
                product_return_moves = sol_return_moves.filtered(
                    lambda rm: rm.product_id.id == inv_line.product_id.id
                )

                _logger.info(
                    "   🎯 Return moves for product %s: %s",
                    inv_line.product_id.display_name,
                    len(product_return_moves),
                )

                # Sum returned quantities
                for rm in product_return_moves:
                    total_returned += rm.product_uom_qty
                    _logger.info(
                        "      ➕ Adding %s from return %s, Total: %s",
                        rm.product_uom_qty,
                        rm.id,
                        total_returned,
                    )

            if total_returned > 0:
                res[inv_line.id] = total_returned
                _logger.info(
                    "✅ Line %s has %s returned units", inv_line.id, total_returned
                )
            else:
                _logger.info("❌ Line %s has no returns", inv_line.id)

        _logger.info("🎯 Final mapping result: %s", res)
        return res

    def _find_original_line_for_nc_line(self, nc_line, original_invoice):
        """Find the original line corresponding to a Credit Note line"""
        _logger.info("🔍 FINDING ORIGINAL LINE for NC line %s", nc_line.id)
        _logger.info(
            "   📋 NC line details: Product: %s, Name: '%s', Display Type: %s, Product ID: %s",
            nc_line.product_id.display_name if nc_line.product_id else "None",
            nc_line.name,
            nc_line.display_type,
            nc_line.product_id.id if nc_line.product_id else "None",
        )

        # DEBUG: Check ALL original lines without filtering
        _logger.info(
            "   🔎 ALL original lines (%s):", len(original_invoice.invoice_line_ids)
        )
        for orig_line in original_invoice.invoice_line_ids:
            _logger.info(
                "      📋 Line %s: Product: %s, Product ID: %s, Name: '%s', Display Type: '%s'",
                orig_line.id,
                orig_line.product_id.display_name if orig_line.product_id else "None",
                orig_line.product_id.id if orig_line.product_id else "None",
                orig_line.name,
                orig_line.display_type,
            )

        # Get product lines - more flexible method
        original_product_lines = original_invoice.invoice_line_ids.filtered(
            lambda l: l.product_id is not None  # Has associated product
        )

        _logger.info("   📊 Lines with product (%s):", len(original_product_lines))
        for orig_line in original_product_lines:
            _logger.info(
                "      📋 Line %s: Product: %s, Product ID: %s, Display Type: '%s'",
                orig_line.id,
                orig_line.product_id.display_name,
                orig_line.product_id.id,
                orig_line.display_type,
            )

        # Method 1: Search by exact Product ID
        if nc_line.product_id:
            matching_lines = original_product_lines.filtered(
                lambda l: l.product_id.id == nc_line.product_id.id
            )
            _logger.info(
                "   🔎 Search by Product ID %s: %s lines found",
                nc_line.product_id.id,
                len(matching_lines),
            )

            if matching_lines:
                _logger.info(
                    "✅ Found original line by Product ID: %s", matching_lines[0].id
                )
                return matching_lines[0]

        # Method 2: If only one product line in both invoices, use that
        nc_product_lines = self.invoice_line_ids.filtered(
            lambda l: l.product_id is not None
        )
        if len(original_product_lines) == 1 and len(nc_product_lines) == 1:
            _logger.info(
                "✅ Single product line available: %s", original_product_lines[0].id
            )
            return original_product_lines[0]

        # Method 3: Search by exact name
        if nc_line.name:
            matching_lines = original_product_lines.filtered(
                lambda l: l.name and l.name.strip() == nc_line.name.strip()
            )
            _logger.info(
                "   🔎 Search by exact name '%s': %s lines found",
                nc_line.name,
                len(matching_lines),
            )

            if matching_lines:
                _logger.info(
                    "✅ Found original line by exact name: %s", matching_lines[0].id
                )
                return matching_lines[0]

        # Method 4: Search by name similarity
        if nc_line.name:
            matching_lines = original_product_lines.filtered(
                lambda l: l.name
                and (
                    nc_line.name.strip() in l.name.strip()
                    or l.name.strip() in nc_line.name.strip()
                )
            )
            _logger.info(
                "   🔎 Search by name similarity: %s lines found", len(matching_lines)
            )

            if matching_lines:
                _logger.info(
                    "✅ Found original line by name similarity: %s",
                    matching_lines[0].id,
                )
                return matching_lines[0]

        _logger.warning("❌ Could not find original line for NC line %s", nc_line.id)
        return None

    @api.model_create_multi
    def create(self, vals_list):
        _logger.info("🎯🎯🎯 STARTING ACCOUNT.MOVE CREATE 🎯🎯🎯")
        _logger.info("📦 Moves to create: %s", len(vals_list))

        moves = super().create(vals_list)

        for move in moves:
            _logger.info(
                "🔍 Analyzing move %s: type=%s, reversed_entry_id=%s",
                move.id,
                move.move_type,
                move.reversed_entry_id,
            )

            # Only intervene in customer Credit Notes created by reversal
            if move.move_type != "out_refund" or not move.reversed_entry_id:
                _logger.info(
                    "⏩ Skipping move %s - Not a customer Credit Note by reversal",
                    move.id,
                )
                continue

            _logger.info(
                "🔄 PROCESSING NC %s created from invoice %s",
                move.name,
                move.reversed_entry_id.name,
            )

            original = move.reversed_entry_id
            _logger.info(
                "🔄 Processing NC %s created from invoice %s", move.name, original.name
            )

            returned_map = self._get_returned_qty_by_invoice_line(original)

            if returned_map:
                _logger.info("✅ Returns found: %s", returned_map)
                # THERE ARE RETURNS: Adjust lines and lock
                lines_to_unlink = self.env["account.move.line"]
                lines_to_keep = self.env["account.move.line"]

                _logger.info("📋 Processing %s NC lines", len(move.invoice_line_ids))

                for line in move.invoice_line_ids:
                    _logger.info(
                        "🔍 NC line ID: %s, Product: %s, Display Type: %s, Quantity: %s",
                        line.id,
                        line.product_id.display_name if line.product_id else "None",
                        line.display_type,
                        line.quantity,
                    )

                    # Only process lines that have products (not display lines)
                    if not line.product_id:
                        _logger.info(
                            "   ⏩ Skipping line without product: %s (type: %s)",
                            line.id,
                            line.display_type,
                        )
                        continue

                    # Use improved method to find original line
                    original_line = move._find_original_line_for_nc_line(line, original)

                    if not original_line:
                        _logger.warning(
                            "⚠️ Line %s could not find associated original line", line.id
                        )
                        # If we can't find the original line, assume no return
                        lines_to_unlink += line
                        continue

                    qty_dev = returned_map.get(original_line.id, 0.0)
                    _logger.info(
                        "📦 NC line %s (original %s): returned quantity = %s",
                        line.id,
                        original_line.id,
                        qty_dev,
                    )

                    if not qty_dev:
                        # Delete line without returns
                        _logger.info("🗑️ Deleting line %s without returns", line.id)
                        lines_to_unlink += line
                    else:
                        # Adjust quantity and mark as locked
                        qty_final = min(qty_dev, line.quantity or 0.0)
                        line.quantity = qty_final
                        line.is_return_nc_locked = True
                        lines_to_keep += line
                        _logger.info(
                            "🔒 Line %s locked with quantity %s", line.id, qty_final
                        )

                # Delete lines without returns
                if lines_to_unlink:
                    _logger.info(
                        "🗑️ Deleting %s lines without returns", len(lines_to_unlink)
                    )
                    lines_to_unlink.unlink()

                # Verify remaining lines using product as criterion
                prod_lines = move.invoice_line_ids.filtered(
                    lambda l: l.product_id is not None
                )
                _logger.info("📊 Product lines after processing: %s", len(prod_lines))

                if not prod_lines:
                    raise UserError(
                        _(
                            "No returned items found to generate the credit note. "
                            "Please cancel this Credit Note and create one manually."
                        )
                    )

                # Tax recalculation methods for different Odoo versions
                try:
                    # Odoo 17+
                    move._recompute_tax_lines()
                    _logger.info("✅ Tax lines recalculated (_recompute_tax_lines)")
                except AttributeError:
                    try:
                        # Odoo 16 and earlier
                        move._recompute_dynamic_lines(recompute_all_taxes=True)
                        _logger.info(
                            "✅ Tax lines recalculated (_recompute_dynamic_lines)"
                        )
                    except AttributeError:
                        try:
                            # Alternative method
                            move.line_ids._onchange_price_subtotal()
                            _logger.info(
                                "✅ Tax lines recalculated (_onchange_price_subtotal)"
                            )
                        except Exception:
                            # If nothing works, force amount recalculation
                            move._compute_amount()
                            _logger.info("✅ Amounts recalculated (_compute_amount)")

                # Chatter message
                resumen = []
                for l in prod_lines:
                    resumen.append(f"- {l.product_id.display_name}: {l.quantity}")
                move.message_post(
                    body=_(
                        "✅ Credit Note automatically adjusted based on returns:%s"
                        "🔒 Quantities are locked because there are associated returns."
                    )
                    % "".join(resumen)
                )

            else:
                # NO RETURNS: Leave everything editable
                _logger.info("❌ No returns found for this invoice")
                move.message_post(
                    body=_(
                        "📝 No linked returns detected. "
                        "The credit note contains all original lines and is editable."
                    )
                )

        return moves

    def write(self, vals):
        # Prevent editing in Credit Notes with locked lines
        if "invoice_line_ids" in vals:
            for move in self:
                if move.move_type != "out_refund":
                    continue

                # Check if any line is locked
                has_locked_lines = any(
                    line.is_return_nc_locked
                    for line in move.invoice_line_ids
                    if not line.display_type
                )

                if not has_locked_lines:
                    continue

                # Check each command in the lines
                for command in vals["invoice_line_ids"]:
                    if isinstance(command, (tuple, list)) and len(command) >= 2:
                        operation = command[0]

                        if operation in (1, 2):  # UPDATE or DELETE
                            line_id = command[1]
                            line = self.env["account.move.line"].browse(line_id)

                            if line.is_return_nc_locked:
                                if operation == 1:  # UPDATE
                                    line_vals = command[2] if len(command) > 2 else {}
                                    if "quantity" in line_vals:
                                        raise UserError(
                                            _(
                                                "❌ Cannot modify quantity in lines with associated returns.\n\n"
                                                "The quantity %s of product %s is locked because there is a return of %s units.\n\n"
                                                "To modify this credit note, first cancel the associated returns."
                                            )
                                            % (
                                                line.quantity,
                                                line.product_id.display_name,
                                                line.quantity,
                                            )
                                        )
                                elif operation == 2:  # DELETE
                                    raise UserError(
                                        _(
                                            "❌ Cannot delete lines with associated returns.\n\n"
                                            "The line for product %s has a return of %s units.\n\n"
                                            "To delete this line, first cancel the associated return."
                                        )
                                        % (line.product_id.display_name, line.quantity)
                                    )

                        elif operation == 0:  # CREATE
                            raise UserError(
                                _(
                                    "❌ Cannot add new lines to a credit note with returns.\n\n"
                                    "This Credit Note was automatically generated based on existing returns.\n\n"
                                    "To add additional lines, create a new manual credit note."
                                )
                            )

        return super().write(vals)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    is_return_nc_locked = fields.Boolean(
        string="Line Locked by Return",
        help="Indicates if the quantity is locked due to associated returns",
        default=False,
    )
