# -*- coding: utf-8 -*-

from openerp import models, fields, api
import openerp.addons.decimal_precision as dp


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.one
    def _cal_msi(self):
        if self.is_roll_order:
            exact = 0
            master = 0
            lam = 0
            for rec in self.roll_order_lines:
                if rec.product_roll_id.product_tmpl_id.categ_id.extra_info == "exact":
                    exact += rec.msi
                elif rec.product_roll_id.product_tmpl_id.categ_id.extra_info == "master":
                    master += rec.msi
                elif rec.product_roll_id.product_tmpl_id.categ_id.extra_info == "lamination":
                    lam += rec.msi
            self.msi_sub_exact = exact
            self.msi_sub_master = master
            self.msi_sub_lam = lam/5
            self.msi_sub_total = self.msi_sub_exact+self.msi_sub_master+self.msi_sub_lam


    is_roll_order = fields.Boolean("Pedido de rollos", copy=True)
    roll_order_lines = fields.One2many("purchase.order.line.roll", "roll_order_id", copy=True)
    msi_sub_exact = fields.Float("Subtotal Plan Exact", compute=_cal_msi, default=0)
    msi_sub_master = fields.Float("Subtotal Master Rolls", compute=_cal_msi, default=0)
    msi_sub_lam = fields.Float(u"Subtotal Laminación", compute=_cal_msi, default=0)
    msi_sub_total = fields.Float("Total MSI", compute=_cal_msi, default=0)


    @api.multi
    def button_confirm(self):

        for rec in self:
            if rec.is_roll_order:
                [line.unlink() for line in rec.order_line]
                for roll in rec.roll_order_lines:
                    new_order_line = self.env["purchase.order.line"].new({"product_id": roll.product_roll_id.id,
                                                                          "order_id": roll.roll_order_id.id})
                    new_order_line.onchange_product_id()
                    new_order_line.product_qty = roll.rolls
                    new_order_line.price_unit = roll.roll_price
                    new_order_line.create(new_order_line._convert_to_write(new_order_line._cache))
                    rec._amount_all()

                    
        return super(PurchaseOrder, self).button_confirm()


class PurchaseOrderLine(models.Model):
    _name = 'purchase.order.line.roll'

    @api.multi
    def _cal_msi(self):
        for rec in self:
            if rec.product_roll_id:
                attrs = dict([(att.attribute_id.name, att.name) for att in rec.product_roll_id.attribute_value_ids])
                rec.ancho = float(attrs["Banda"])
                rec.largo = float(attrs["Largo"])
                rec.msi = rec.rolls*rec.ancho*(12*rec.largo/1000)
                rec.total_price_msi = rec.msi*rec.price_msi
                rec.roll_price = rec.total_price_msi/rec.rolls

    roll_order_id = fields.Many2one("purchase.order")
    product_roll_id = fields.Many2one('product.product', string='Product', domain=[('purchase_ok', '=', True),('categ_id.extra_info','in',('exact','master','lamination'))], change_default=True, required=True)
    rolls = fields.Float("Rollos", default=1)
    ancho = fields.Float(u'Ancho"', compute=_cal_msi)
    largo = fields.Float(u"Largo'", compute=_cal_msi)
    msi = fields.Float("MSI", compute=_cal_msi)
    price_msi = fields.Float(string='Precio', required=True, digits=dp.get_precision('Product Price'), default=1)
    total_price_msi = fields.Float(string='Total', required=True, digits=dp.get_precision('Product Price'), default=1, compute=_cal_msi)
    roll_price = fields.Float(string='Precio por rollo', required=True, digits=dp.get_precision('Product Price'), default=1, compute=_cal_msi)

    @api.onchange("rolls")
    def onchange_rolls(self):
        self._cal_msi()

    @api.onchange("price_msi")
    def onchange_price_msi(self):
        self._cal_msi()

    @api.onchange("product_roll_id")
    def onchange_roll_order_id(self):
        if self.product_roll_id:
            attrs = dict([(att.attribute_id.name, att.name) for att in self.product_roll_id.attribute_value_ids])
            if attrs.keys() == [u'Largo', u'Banda']:
                self._cal_msi()
            else:
                return {"value": {"product_roll_id": False},
                        'warning': {'title': u"Error de configuración", 'message': u"El rollo selccionado debe tener las variantes Largo y Ancho definidas"}
                        }
