/**
 * Created by nmew on 8/28/14.
 */
define(['backbone', 'models/pose', 'localstorage'], function(Backbone, Pose) {
    return Backbone.Collection.extend({
        model: Pose,
        localStorage: new Backbone.LocalStorage("poses-backbone")
    });
});