/**
 * Created by nmew on 9/4/14.
 */
define([
    'jquery',
    'backbone',
    'views/slider',
    'moleculeDisplayOptions'], function($, Backbone, Slider) {
    return Backbone.View.extend({
        ligandSlider: null,
        representations: [
            { 'id': "dots", 'name': "Dots", 'show': "dots ?;", 'valueMinMax': [100, 700], 'hide': "dots off;", 'img': "img/ico/dots.png"},
            { 'id': "spacefill", 'name': "Spacefill", 'show': "cpk on;spacefill ?;", 'valueMinMax': [100, 700], 'hide': "cpk off;", 'img': "img/ico/spacefill.png"},
            { 'id': "wireframe", 'name': "Wireframe", 'show': "wireframe ?;", 'valueMinMax': [0, 100], 'hide': "wireframe off;", 'img': "img/ico/sticks.png"}
        ],
        initialize: function(options) {
            this.vent = options.vent;   // message bus
            _.bindAll(this, "onDisplayOptionShow", "onDisplayOptionHide");
        },
        render: function() {
            var renderSettings = this.model;

            var minMax = _.findWhere(this.representations, {id: renderSettings.get('ligandDisplayRepresentation')}).valueMinMax;

            this.ligandSlider = new Slider({
                el: this.$el.find('#ligandDiameterSlider'),
                model: renderSettings,
                attributes: {
                    modelParam: 'ligandDisplayValue',
                    min: minMax[0],
                    max: minMax[1]
                }
            }).render();

            this.$el.find("#ligandDisplayOptions").displayOptions({
                atoms: [
                    { 'id': 'lig', 'name': "", 'select': '' }
                ],
                representations: this.representations,
                defaultDisplay: ['display-lig-as-' + renderSettings.get('ligandDisplayRepresentation')],
                init: function (event, data) {
//                    this.vent.trigger('ligandScript', data.jmolScript);
                },
                show: this.onDisplayOptionShow,
                hide: this.onDisplayOptionHide
            });

            return this;
        },
        remove: function() {
            this.ligandSlider.remove();
            this.$el.find("#ligandDisplayOptions").displayOptions('destroy');
            this.undelegateEvents();
            this.stopListening();
            return this;
        },
        onDisplayOptionHide: function (event, data) {
            this.vent.trigger('ligandScript', data.jmolScript);
            this.ligandSlider.setOptions("disable");
        },
        onDisplayOptionShow: function (event, data) {
            if (data.values) {
                this.model.set('ligandDisplayRepresentation', data.values.representation);
                this.vent.trigger('ligandScript', data.jmolScript);
                if (data.values.value === null) {
                    this.ligandSlider.setOptions("disable");
                } else {
                    this.ligandSlider.setOptions("enable");
                    this.ligandSlider.setOptions("option", "min", data.values.min);
                    this.ligandSlider.setOptions("option", "max", data.values.max);
                    // todo: prevent the slider change from firing
                    this.ligandSlider.setOptions("option", "values", [data.values.value]);
                }
            }
        }
    });
});
