/**
 * Created by nmew on 8/14/14.
 */
define([
    'underscore',
    'backbone'
], function(_, Backbone){
    var Point = Backbone.Model.extend({
        idAttribute: 'description',
        defaults: {
            alignment: null,
            molecule: null,
            molId: null,
            description: null,
            residueType: null,
            x: null,
            y: null,
            z: null
        },
        getLigand: function(){
            return this.get('description').split("_")[3];
        },
        getName: function(){
            return  "m" + this.get('description').split("_")[4] + this.get('residueType') ;
        },
        constructor: function() {
            this.on('change:alignment', this.setListenerOnAlignmentChanges, this);
            Backbone.Model.apply(this, arguments);
            this.set('ligand', this.getLigand());
            this.set('name', this.getName());
        },
        setListenerOnAlignmentChanges: function() {
            if(this.get('alignment')) {
                this.get('alignment').on('change', function(){
                    this.trigger('change', this);
                }, this);
            }
        },
        parse: function(data, options) {
            var ptfRow = data.rowStr.split(data.delim);
            return {
                molecule: data.molecule,
                molId: ptfRow[0],
                x: ptfRow[1],
                y: ptfRow[2],
                z: ptfRow[3],
                description: ptfRow[5],
                residueType: ptfRow[7]
            };
        }
    });
    // Return the model for the module
    return Point;
});