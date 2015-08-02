/**
 * Created by nmew on 8/14/14.
 */
define([
    'backbone',
    'models/point'
], function(Backbone, Point){
    return Backbone.Collection.extend({
        model: Point,
        comparator: function(point) {
            // any 2 points are compared by their alignment scores or treated as large values otherwise
            return point.has('alignment') ? point.get('alignment').get('score') : 100;
        }
    });
});