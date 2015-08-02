/**
 * Created by nmew on 8/22/14.
 */
define([
    'jquery',
    'underscore',
    'backbone',
    'views/alignmentTable',
    'views/ligandRenderTools',
    'views/moleculeRenderTools',
    'views/slider'
], function($, _, Backbone, AlignmentTable, LigandRenderTools, MoleculeRenderTools, Slider) {

    var HqButton = Backbone.View.extend({
        events: { "click": "toggleHQ" },
        render: function(){
            if(this.model.get('hq')) { this.$el.addClass('btn-primary'); }
            return this;
        },
        toggleHQ: function() {
            this.model.set('hq', !this.model.get('hq'));
            this.$el.toggleClass('btn-primary');
            return this;
        },
        remove: function() {
            this.$el.removeClass('btn-primary');
            this.stopListening();
            this.undelegateEvents();
            return this;
        }
    });

    return Backbone.View.extend({
        initialize: function(options) {
            this.vent = options.vent;
            this.molecules = options.molecules;
            this.alignments = options.alignments;
            this.renderSettings = options.renderSettings;
            this.views = [];
        },
        render: function() {
            // animate show
            this.$el.addClass('rendered');

            this.views.push(new AlignmentTable({
                el: this.$el.find('#alignmentTable'),
                attributes: {
                    molecules: this.molecules,
                    alignments: this.alignments
                }
            }).render());

            var cutoffSlider = new Slider({
                el: this.$el.find('#scoreCutoffSlider'),
                model: this.renderSettings,
                attributes: {
                    max: (this.alignments.first().get('score') - 0.001) * -1,
                    min: (this.alignments.last().get('score') + 0.001) * -1,
                    step: 0.001,
                    tooltipPlacement: 'top',
                    slideModelParam: 'alignmentScoreCutoffUI',
                    modelParam: 'alignmentScoreCutoff'
                },
                modelValueToUiValue: function(modelValue){ return modelValue * -1; },
                uiValueToModelValue: function(uiValue){ return uiValue * -1; }
            }).render();

            this.listenTo(cutoffSlider, 'sliderChange', function() {
                this.vent.trigger('sliderChange:scoreCutoff');
            });

            this.views.push(cutoffSlider);

            this.views.push(new Slider({
                el: this.$el.find('#ballScaleSlider'),
                model: this.renderSettings,
                attributes: {
                    max: 15,
                    min: 1,
                    step: 0.1,
                    tooltipPlacement: 'top',
                    modelParam: 'ballScale',
                    tooltipValue: 'ui'
                },
                modelValueToUiValue: function(modelValue){ return modelValue * -1; },
                uiValueToModelValue: function(uiValue){ return uiValue * -1; }
            }).render());

            this.views.push(new LigandRenderTools({
                el: this.$el.find('.ligandRenderingTools'),
                vent: this.vent,
                model: this.renderSettings
            }).render());

            this.views.push(new MoleculeRenderTools({
                el: this.$el.find('.moleculeRenderingTools'),
                vent: this.vent,
                model: this.renderSettings
            }).render());

            this.views.push(new HqButton({
                el: this.$el.find('#hqButton'),
                model: this.renderSettings
            }).render());

            return this;
        },
        remove: function() {
            // animate hide
            this.$el.removeClass('rendered');
            // remove inner views
            _.each(this.views, function(view) {
                if(view.remove) {
                    view.remove();
                }
            });
            this.undelegateEvents();
            this.stopListening();
            return this;
        }
    });

});
