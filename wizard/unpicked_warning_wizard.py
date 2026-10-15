# -*- coding: utf-8 -*-
from markupsafe import Markup, escape

from odoo import _, fields, models
from odoo.exceptions import UserError


class UnpickedWarningWizard(models.TransientModel):
    _name = "unpicked.warning.wizard"
    _description = "Aviso de mercadería sin separar al facturar"

    move_ids = fields.Many2many("account.move", string="Facturas")
    warning_html = fields.Html(readonly=True, sanitize=False)
    can_invoice_separated = fields.Boolean(readonly=True)

    def _build_html(self, data):
        rows = Markup("")
        for line in data:
            pickings = ", ".join(line["pickings"].mapped("name")) or "-"
            reason = _("sin stock reservado") if line["unreserved"] else _("en preparación")
            rows += Markup(
                "<tr><td>%s</td><td>%s</td><td class='text-end'>%s</td>"
                "<td class='text-end'>%s</td><td class='text-end text-danger fw-bold'>%s</td>"
                "<td>%s (%s)</td></tr>"
            ) % (
                escape(line["order"].name),
                escape(line["product"].display_name),
                "{:g}".format(line["in_invoice"]),
                "{:g}".format(line["picked"]),
                "{:g}".format(line["pending"]),
                escape(pickings),
                escape(reason),
            )
        header = Markup(
            "<p>%s</p><table class='table table-sm'><thead><tr>"
            "<th>%s</th><th>%s</th><th class='text-end'>%s</th><th class='text-end'>%s</th>"
            "<th class='text-end'>%s</th><th>%s</th></tr></thead><tbody>%s</tbody></table>"
        ) % (
            escape(_("Estás por confirmar una factura con mercadería que todavía no se separó (primer paso de la entrega):")),
            escape(_("Pedido")), escape(_("Producto")), escape(_("En la factura")),
            escape(_("Separado")), escape(_("Sin separar")), escape(_("Operación")), rows,
        )
        return header

    def action_confirm(self):
        self.ensure_one()
        data = self.move_ids._unpicked_lines_data()
        for order in {d["order"] for d in data}:
            products = ", ".join(
                "%s (%s)" % (d["product"].display_name, "{:g}".format(d["pending"]))
                for d in data if d["order"] == order
            )
            order.message_post(body=_(
                "Factura confirmada con mercadería sin separar: %s", products
            ))
        return self.move_ids.action_post()

    def action_invoice_only_separated(self):
        """Recorta el borrador a lo separado: baja la cantidad (o elimina la
        línea) de lo que no se separó. Lo recortado sigue pendiente en el
        pedido, así que la próxima factura creada desde el pedido lo trae."""
        self.ensure_one()
        data = self.move_ids._unpicked_lines_data()
        if any(m.state != "draft" for m in self.move_ids):
            raise UserError(_("Solo se puede recortar una factura en borrador."))
        if not self.move_ids._has_separated_lines():
            raise UserError(_("No hay nada separado para facturar todavía."))
        summary = {}
        for item in data:
            remaining = item["pending"]
            sale_line = item["sale_line"]
            commands = []
            for line in item["invoice_lines"].sorted("id", reverse=True):
                if remaining <= 0:
                    break
                factor = line.product_uom_id._compute_quantity(1.0, sale_line.product_uom)
                qty_sale = line.quantity * factor
                cut = min(qty_sale, remaining)
                new_qty = (qty_sale - cut) / factor
                remaining -= cut
                if new_qty <= 0:
                    commands.append((2, line.id))
                else:
                    commands.append((1, line.id, {"quantity": new_qty}))
            item["invoice"].write({"invoice_line_ids": commands})
            summary.setdefault(item["order"], []).append(
                "%s (%s)" % (item["product"].display_name, "{:g}".format(item["pending"]))
            )
        for order, products in summary.items():
            msg = _("Se facturó solo lo separado. Quedó pendiente de facturar: %s", ", ".join(products))
            order.message_post(body=msg)
            self.move_ids.filtered(lambda m, o=order: o in m.line_ids.sale_line_ids.order_id).message_post(body=msg)
        return {"type": "ir.actions.client", "tag": "soft_reload"}
