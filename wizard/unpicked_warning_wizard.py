# -*- coding: utf-8 -*-
from markupsafe import Markup, escape

from odoo import _, fields, models


class UnpickedWarningWizard(models.TransientModel):
    _name = "unpicked.warning.wizard"
    _description = "Aviso de mercadería sin separar al facturar"

    move_ids = fields.Many2many("account.move", string="Facturas")
    warning_html = fields.Html(readonly=True, sanitize=False)

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
                "{:g}".format(line["ordered"]),
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
            escape(_("Pedido")), escape(_("Producto")), escape(_("Cantidad")),
            escape(_("Separado")), escape(_("Pendiente")), escape(_("Operación")), rows,
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
