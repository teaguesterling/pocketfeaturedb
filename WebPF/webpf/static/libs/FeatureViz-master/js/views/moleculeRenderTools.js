/**
 * Created by nmew on 9/4/14.
 */
define([
    'jquery',
    'backbone',
    'views/slider',
    'moleculeDisplayOptions', 'bootstrap'], function($, Backbone, Slider) {
    return Backbone.View.extend({
        ligandSlider: null,
        initialize: function(options) {
            this.vent = options.vent;   // message bus
            _.bindAll(this, "onDisplayOptionShow", "onDisplayOptionHide");
        },
        render: function() {

            this.zShadeSlider = new Slider({
                el: this.$el.find('div.proteinZShadeSlider'),
                model: this.model,
                attributes: {
                    modelParam: ['slab','zSlab','zDepth'],
                    handlerNames: ['Slab', 'Fog', 'Depth'],
                    handlerText: ['S','F','D']
                },
                modelValueToUiValue: function(modelValue){ return 100 - modelValue; },
                uiValueToModelValue: function(uiValue){ return 100 - uiValue; }
            }).render();

            this.$el.find("div.proteinDisplayOptions").displayOptions({
                atoms: [{ 'id': 'mol', 'name': "", 'select': "select {protein}" }],
                defaultDisplay: ['display-mol-as-' + this.model.get('moleculeDisplayRepresentation')],
                representations: _.reject(
                    $.biojs.displayOptions().options.representations,
                    function(rep) { return rep.id == 'rocket'; }
                ),
                hide: this.onDisplayOptionHide,
                show: this.onDisplayOptionShow
            });

            return this;
        },
        remove: function() {
            this.zShadeSlider.remove();
            this.$("div.proteinDisplayOptions").displayOptions('destroy');
            this.undelegateEvents();
            this.stopListening();
        },
        onDisplayOptionHide: function (event, data) {
            this.model.set('moleculeDisplayRepresentation', null);
            this.vent.trigger('moleculeScript', data.jmolScript);
            console.log(data);
        },
        onDisplayOptionShow: function (event, data) {
            if (data.values) {
                this.model.set('moleculeDisplayRepresentation', data.values.representation);
                this.vent.trigger('moleculeScript', data.jmolScript);
                console.log(data);
            }
        }
    });
});
