# -*- encoding: utf-8 -*-
##############################################################################
#
#    "Product variant multi advanced" module for OpenERP
#    Copyright (C) 2010 Sébastien BEAU <sebastien.beau@akretion.com>
#    @author Alexis de Lattre <alexis.delattre@akretion.com> (convert to
#       single "Generate/Update" button)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import osv, fields
# Lib required to print logs
import netsvc
# Lib to translate error messages
from tools.translate import _
# Lib to eval python code with security
from tools.safe_eval import safe_eval

def get_vals_to_write(vals, fields):
    vals_to_write = {}
    for field in fields:
        if field in vals.keys():
            vals_to_write[field] = vals[field]
    return vals_to_write

#Add your duplicated fields here
duplicated_fields = ['description_sale', 'name']

class product_template(osv.osv):
    _inherit = "product.template"

    def button_generate_variants(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        super(product_template, self).button_generate_variants(cr, uid, ids, context=context)
        product_ids = self.get_products_from_product_template(cr, uid, ids, context=context)
        # generate/update sale description
        logger = netsvc.Logger()
        logger.notifyChannel('product_variant_multi_advanced', netsvc.LOG_INFO, "Starting to generate/update product sale descriptions...")
        self.pool.get('product.product').build_product_sale_description(cr, uid, product_ids, context=context)
        logger.notifyChannel('product_variant_multi_advanced', netsvc.LOG_INFO, "End of the generation/update of product sale descriptions.")
        return True

product_template()

class product_product(osv.osv):
    _inherit = "product.product"

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        if context is None:
            context = {}
        res = super(product_product, self).write(cr, uid, ids, vals.copy(), context=context)

        ids_simple = self.search(cr, uid, [['id', 'in', ids], ['is_multi_variants', '=', False]], context=context)
        ids_multi_variants = list(set(ids).difference(set(ids_simple)))

        if not context.get('iamthechild', False) and ids_simple:
            vals_to_write = get_vals_to_write(vals, duplicated_fields)

            if vals_to_write:
                obj_tmpl = self.pool.get('product.template')
                ctx = context.copy()
                ctx['iamthechild'] = True
                for product in self.read(cr, uid, ids_simple, ['is_multi_variants', 'product_tmpl_id'], context=context):
                    obj_tmpl.write(cr, uid, [product['product_tmpl_id'][0]], vals_to_write, context=ctx)
        return res

    def create(self, cr, uid, vals, context=None):
        #TAKE CARE for inherits objects openerp will create firstly the product_template and after the product_product
        # and so the duplicated fields will be on the product_template and not on the product_product
        ids = super(product_product, self).create(cr, uid, vals.copy(), context=context) #take care to use vals.copy() if not the vals will be changed by calling the super method
        ####### write the value in the product_product
        if context is None:
            context = {}
        ctx = context.copy()
        ctx['iamthechild'] = True
        vals_to_write = get_vals_to_write(vals, ['name']+duplicated_fields)
        if vals_to_write:
            self.write(cr, uid, ids, vals_to_write, context=ctx)
        return ids

    def build_product_sale_description(self, cr, uid, ids, context=None):
        return self.build_product_field(cr, uid, ids, 'description_sale', context=None)

    def build_product_name(self, cr, uid, ids, context=None):
        return self.build_product_field(cr, uid, ids, 'name', context=None)

    def build_product_field(self, cr, uid, ids, field, context=None):
        if context is None:
            context = {}
        def get_description_sale(product):
            return self.parse(cr, uid, product, product.product_tmpl_id.description_sale, context=context)

        def get_name(product):
            if context.get('variants_values', False):
                return (product.product_tmpl_id.name or '' )+ ' ' + (context['variants_values'][product.id] or '')
            return (product.product_tmpl_id.name or '' )+ ' ' + (product.variants or '')

        context['is_multi_variants']=True
        obj_lang=self.pool.get('res.lang')
        lang_ids = obj_lang.search(cr, uid, [('translatable','=',True)], context=context)
        lang_code = [x['code'] for x in obj_lang.read(cr, uid, lang_ids, ['code'], context=context)]
        for code in lang_code:
            context['lang'] = code
            for product in self.browse(cr, uid, ids, context=context):
                new_field_value = eval("get_" + field + "(product)") # TODO convert to safe_eval
                cur_field_value = safe_eval("product." + field, {'product': product})
                if new_field_value != cur_field_value:
                    self.write(cr, uid, product.id, {field: new_field_value}, context=context)
        return True

    _columns = {
        'name': fields.char('Name', size=128, translate=True, select=True),
        'description_sale': fields.text('Sale Description', translate=True),
    }
product_product()


