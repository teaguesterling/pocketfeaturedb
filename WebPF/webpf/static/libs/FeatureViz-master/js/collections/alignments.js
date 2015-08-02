/**
 * Created by nmew on 8/14/14.
 */
define([
    'backbone',
    'models/alignment',
    'localstorage'
], function(Backbone, Alignment){
    return Backbone.Collection.extend({
        localStorage: new Backbone.LocalStorage("alignments-backbone"),
        model: Alignment,
        comparator: function(a) {
            return +a.get('score');
        }
    });
});