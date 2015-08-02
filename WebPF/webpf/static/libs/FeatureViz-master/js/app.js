/**
 * Created by nmew on 8/14/14.
 */
// Filename: app.js
// todo: rename to FeatureViz.js ?
define([
    'jquery',
    'underscore',
    'backbone',
    'collections/points',
    'collections/alignments',
    'collections/molecules',
    'models/point',
    'models/alignment',
    'models/featureViz',
    'views/moleculeVizualizersContainer',
    'views/renderTools',
    'chroma',
    /*'models/molecule',*/
    'promise','bootstrap', 'jmol'
    /*'router', // Request router.js*/
], function($, _, Backbone, Points, Alignments, Molecules, Point, Alignment, FeatureVizSettings, VizContainer, RenderTools, dataLoader){
    var FV = {};

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

    var showError = function(errorStr) {
        var errorElem = document.getElementById('errorMessages');
        errorElem.innerHTML = 'Error: ' + errorStr;
        errorElem.className = errorElem.className.replace('hidden', ' ');
    };

    var initialize = function(options) {
        this.FV = this.model;
        // Pass in our Router module and call it's initialize function
        // Router.initialize();
        FV.alignments.forEach(function (align) {
//                align.on('changeApprisal', function(){console.log('alignment changeApprisal: ', arguments);});
                align.listenTo(FV.featureVizSettings, 'change:alignmentScoreCutoffUI change:alignmentScoreCutoff', function(fvs, scoreCutoff){
//                    console.log('change:alignmentScoreCutoffUI', arguments, this);
                    this.set('cutoff', scoreCutoff < this.get('score'), {ui: true});
            });
            return FV;
        });


        // initialize Views
        // vizualizer and buttons
        new VizContainer({
            el: document.getElementById('vizCanvas'),
            vent: FV.vent,
            model: FV.featureVizSettings,
            collection: FV.molecules,
            alignments: FV.alignments
        }).render();

        // toolbar
        new RenderTools({
            el: document.getElementById('vizTools'),
            vent: FV.vent,
            molecules: FV.molecules,
            alignments: FV.alignments,
            renderSettings: FV.featureVizSettings
        }).render();
    };

    var resetAndReload = function() {

    };

    return {
        initialize: initialize,
        resetAndReload: resetAndReload
    };
},function(err){ console.error(err); });
