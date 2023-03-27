//odoo.define('prixgen_custom_aged_receivable_email.receivable_report', function (require) {
//    "use strict";
//
//    var AgedReceivable = require('account_reports.account_report');
//
//    var core = require('web.core');
//
//    var QWeb = core.qweb;
//    var _t = core._t;
//
//    AgedReceivable.include({
//        renderButtons: function() {
//            var self = this;
//            console.log(self);
//            if(self.report_model === "account.aged.receivable"){
//                this.buttons.splice(2, 0, {name: 'Send By Email', sequence: '3', action: 'custom_send_mail'});
//            }
//            this.$buttons = $(QWeb.render("accountReports.buttons", {buttons: this.buttons}));
//            // bind actions
//            _.each(this.$buttons.siblings('button'), function(el) {
//                console.log(el);
//                $(el).click(function() {
//                    self.$buttons.attr('disabled', true);
//                    return self._rpc({
//                            model: self.report_model,
//                            method: $(el).attr('action'),
//                            args: [self.financial_id, self.report_options],
//                            context: self.odoo_context,
//                        })
//                        .then(function(result){
//                            var doActionProm = self.do_action(result);
//                            self.$buttons.attr('disabled', false);
//                            return doActionProm;
//                        })
//                        .guardedCatch(function() {
//                            self.$buttons.attr('disabled', false);
//                        });
//                });
//            });
//            return this.$buttons;
//        },
// });
//})