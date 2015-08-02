/**
 * Created by nmew on 8/14/14.
 */
define([
    'underscore',
    'backbone'
], function(_, Backbone){
    var Molecule = Backbone.Model.extend({
        defaults: {
            id: null,
            align: null,
            pdb: null,
            ptf: null,
            dssp: null,
            ff: null,
            points: null,
            comparisonOrder: null
        }
    });
    // Return the model for the module
    return Molecule;
});