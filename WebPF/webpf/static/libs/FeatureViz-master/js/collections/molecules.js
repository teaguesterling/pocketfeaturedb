/**
 * Created by nmew on 8/14/14.
 */
define([
    'backbone',
    'models/molecule'
], function(Backbone, Molecule){
    return Backbone.Collection.extend({
        model: Molecule,
        comparator: function(molecule) {
            return molecule.get('comparisonOrder');
        }
    });
});