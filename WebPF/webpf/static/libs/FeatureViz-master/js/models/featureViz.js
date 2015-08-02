/**
 * Created by nmew on 8/22/14.
 */
// todo: rename file 'renderSettings'
define(['backbone'], function(Backbone){
    return Backbone.Model.extend({
        defaults: {
            hq: false,
            alignmentScoreCutoff: -0.1,
            alignmentScoreCutoffUI: -0.1,
            ligandDisplayRepresentation: 'wireframe',
            ligandDisplayValue: 50,
            moleculeDisplayRepresentation: 'cartoon',
            ballScale: -10,
            slab: 70,
            zSlab: 49,
            zDepth: 0,
            lq_hermiteLevel: 1,
            hq_hermiteLevel: 1,
            export_hermiteLevel: 5
        }
    });
});
