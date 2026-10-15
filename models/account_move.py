# -*- coding: utf-8 -*-
from odoo import _, models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _unpicked_lines_data(self):
        """Productos de las facturas de venta (no POS) cuyo pedido todavía no
        pasó el primer paso de la entrega.

        Primer paso = movimientos sin movimiento origen (p. ej. D3/PICK).
        Devuelve una lista de dicts, uno por línea de pedido con faltante.
        """
        data = []
        for move in self:
            if move.move_type != "out_invoice":
                continue
            # Nada que ver con POS.
            if "pos_order_ids" in move._fields and move.pos_order_ids:
                continue
            sale_lines = move.invoice_line_ids.sale_line_ids
            for sale_line in sale_lines:
                product = sale_line.product_id
                if not product or product.type != "consu":
                    continue
                moves = sale_line.move_ids.filtered(lambda m: m.state != "cancel")
                if not moves:
                    continue
                first_step = moves.filtered(lambda m: not m.move_orig_ids)
                done = sum(
                    m.product_uom._compute_quantity(m.quantity, sale_line.product_uom)
                    for m in first_step.filtered(lambda m: m.state == "done")
                )
                pending = sale_line.product_uom_qty - done
                if pending <= 0:
                    continue
                waiting = first_step.filtered(lambda m: m.state != "done")
                data.append({
                    "invoice": move,
                    "order": sale_line.order_id,
                    "product": product,
                    "ordered": sale_line.product_uom_qty,
                    "picked": done,
                    "pending": pending,
                    "pickings": waiting.picking_id,
                    "unreserved": bool(
                        waiting.filtered(lambda m: m.state in ("confirmed", "waiting"))
                    ),
                })
        return data

    def action_post_con_aviso_separacion(self):
        """Botón "Confirmar" del formulario de factura: si hay mercadería sin
        separar abre un aviso (no bloquea: se puede confirmar igual)."""
        data = self._unpicked_lines_data()
        if not data:
            return self.action_post()
        wizard = self.env["unpicked.warning.wizard"].create({
            "move_ids": [(6, 0, self.ids)],
            "warning_html": self.env["unpicked.warning.wizard"]._build_html(data),
        })
        return {
            "type": "ir.actions.act_window",
            "name": _("Mercadería sin separar"),
            "res_model": "unpicked.warning.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }
