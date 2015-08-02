/**
 * Created by nmew on 8/28/14.
 */
define(['backbone'], function(Backbone) {
    return Backbone.Model.extend({
        defaults: {
            name: '',
            scripts: [],
            active: false
        }
    });
});