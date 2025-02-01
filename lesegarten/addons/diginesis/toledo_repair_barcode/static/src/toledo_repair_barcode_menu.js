/** @odoo-module **/

import AbstractAction from 'web.AbstractAction';
import core from 'web.core';
import Dialog from 'web.Dialog';
import Session from 'web.session';
import * as BarcodeScanner from '@web_enterprise/webclient/barcode/barcode_scanner';

const _t = core._t;

const MainMenu = AbstractAction.extend({
    contentTemplate: 'toledo_repair_barcode_main_menu',

    events: {
        "click .o_toledo_repair_barcode_menu": function () {
            this.trigger_up('toggle_fullscreen');
            this.trigger_up('show_home_menu');
        },
        "click .o_toledo_repair_mobile_barcode": async function() {
            const barcode = await BarcodeScanner.scanBarcode();
            if (barcode){
                this._onBarcodeScanned(barcode);
                if ('vibrate' in window.navigator) {
                    window.navigator.vibrate(100);
                }
            } else {
                this.displayNotification({
                    type: 'warning',
                    message:_t("Please, Scan again !"),
                });
            }
        }
    },

    init: function (parent, action) {
        this._super(...arguments);
        this.message_demo_barcodes = action.params.message_demo_barcodes;
        this.mobileScanner = BarcodeScanner.isBarcodeScannerSupported();
    },

    willStart: async function () {
        await this._super(...arguments);
    },

    start: function() {
        core.bus.on('barcode_scanned', this, this._onBarcodeScanned);
        this._super();
    },

    destroy: function () {
        core.bus.off('barcode_scanned', this, this._onBarcodeScanned);
        this._super();
    },

    _onBarcodeScanned: function (barcode) {
        if (!$.contains(document, this.el)) {
            return;
        }
        Session.rpc('/toledo_repair_barcode/scan_from_main_menu', { barcode }).then(result => {
            if (result.action) {
                this.do_action(result.action);
            } else if (result.warning) {
                this.displayNotification({ title: result.warning, type: 'danger' });
            }
        });
    },
});

core.action_registry.add('toledo_repair_barcode_main_menu', MainMenu);

export default MainMenu;
