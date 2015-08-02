/**
 * Created by nmew on 9/11/14.
 */
define([
    'jquery',
    'underscore',
    'backbone',
    'models/featureViz',
    'views/moleculeVizualizersContainer',
    'views/renderTools',
    'jmol'
], function($, _, Backbone, FeatureVizSettings, VizContainer, RenderTools) {
    var FV = {};

    // todo: use these as default to featurevizsettings in model
    FV.defaults = {
        moleculeDisplayRepresentation: 'cartoon',
        ligandDisplayRepresentation: 'wireframe',
        ligandDiameter: 50,
        ballScale: -10,
        slab: 70,
        zSlab: 49,
        zDepth: 0
    };
    FV.featureVizSettings = new FeatureVizSettings(FV.defaults);

    // todo: uh, put this somewhere else
    var showError = function(errorStr) {
        var errorElem = document.getElementById('errorMessages');
        errorElem.innerHTML = 'Error: ' + errorStr;
        errorElem.className = errorElem.className.replace('hidden', ' ');
    };

    return Backbone.View.extend({
        initialize: function(options) {
            console.log('initializing appview');
            this.FV = this.model;
            // Pass in our Router module and call it's initialize function
            // Router.initialize();

            this.FV.alignments.forEach(function (align) {
                //                align.on('changeApprisal', function(){console.log('alignment changeApprisal: ', arguments);});
                align.listenTo(this.FV.featureVizSettings, 'change:alignmentScoreCutoffUI change:alignmentScoreCutoff', function (fvs, scoreCutoff) {
                    //                    console.log('change:alignmentScoreCutoffUI', arguments, this);
                    this.set('cutoff', scoreCutoff < this.get('score'), {ui: true});
                });
            }, this);
            console.log('appview initialized', this);
        },
        render: function() {
            console.log('rendering appview', this);
            // initialize Views
            // vizualizer and buttons
            this.vizContainer = new VizContainer({
                el: this.$el.find('#vizCanvas'),
                model: this.FV
            }).render();

            // toolbar
            this.renderTools = new RenderTools({
                el: this.$el.find('#vizTools'),
                vent: this.FV.vent,
                molecules: this.FV.molecules,
                alignments: this.FV.alignments,
                renderSettings: this.FV.featureVizSettings
            }).render();

            var that = this;
            window.killVizContainer = function(){
                that.vizContainer.remove();
            };
            return this;
        },

        remove: function () {
            console.log('resetAndReload', arguments);
            // kill vizContainer
            this.vizContainer.remove();
            // kill renderTools
            this.renderTools.remove();
            // remove listeners
            this.undelegateEvents();
            this.stopListening();

            return this;
        }
    });
});
