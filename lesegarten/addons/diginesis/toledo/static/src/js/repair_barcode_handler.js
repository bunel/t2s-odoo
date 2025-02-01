odoo.define('toledo.RepairBarcodeHandler', function (require) {
"use strict";

var core = require('web.core');
var AbstractField = require('web.AbstractField');
var field_registry = require('web.field_registry');
var FormController = require('web.FormController');

var _t = core._t;

FormController.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Method called when a record is already found
     *
     * @private
     * @override
     * @param {Object} candidate (already exists in the x2m)
     * @param {Object} record
     * @param {string} barcode
     * @param {Object} activeBarcode
     * @returns {Promise}
     */
    _barcodeWithoutCandidate: function (record, barcode, activeBarcode) {
        if (activeBarcode.widget === 'repair_barcode_handler') {
            var self = this;

            var rpcProm = self._rpc({
                model: 'repair.barcode.scan',
                method: 'go_serial_number_from_barcode',
                args: [[], barcode],
            });
            rpcProm.then(function (action) {
                // the function returns an action (wizard)
                self._barcodeStopListening();
                self.do_action(action, {});
            });
            return rpcProm;
        }
        return this._super.apply(this, arguments);
    },
});


var RepairBarcodeHandler = AbstractField.extend({
    init: function() {
        this._super.apply(this, arguments);

         this.trigger_up('activeBarcode', {
            name: this.name,
            commands: {
                barcode: '_barcodeAddX2MQuantity',
            }
        });
    },
});

field_registry.add('repair_barcode_handler', RepairBarcodeHandler);

return RepairBarcodeHandler;

});
