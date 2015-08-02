/**
 * Created by nmew on 8/14/14.
 */
define([
    'underscore',
    'backbone',
    'chroma'
], function(_, Backbone, chroma){
    // todo: mutator that prevents highlighted being set to true if cutoff == true
    return Backbone.Model.extend({
        defaults: {
//            molecules: null,
            pointDescriptions: null,
            points: null,
            score: null,
            color: null,
            highlighted: true,
            visible: true,
            hidden: false,
            cutoff: false
        },
        setVisibility: function(){
            var attrs = {
                visible: (!this.get('hidden') && !this.get('cutoff'))
            };
            if(!attrs.visible) {
                attrs.highlighted = false;
            }
            this.set(attrs);
        },
        setColorAttributes: function(){
            var lightColor = this.get('color');
            /* http://www.w3.org/TR/WCAG20/#visual-audio-contrast-contrast */
//            console.log(lightColor.hex(), chroma.contrast(lightColor, 'black'));
            if(chroma.contrast(lightColor, 'black') < 7) {
                lightColor = lightColor.brighter(18);
//                lightColor = lightColor.brighten();
//                console.log(lightColor.hex(), chroma.contrast(lightColor, 'black'));
            }

            this.set({
                hexColor: this.get('color').hex(),
                lighterHexColor: lightColor.hex(),
                darkerHexColor: this.get('color').darken().hex()
            }, {silent: true});

        },
        initialize: function() {
            // give points the alignment value
//            console.log('this in constructor', this);
            _.forEach(this.get('points'), function(p){
//                console.log('this in forEach', this);
                p.set({'alignment': this});
            }, this);
            // set the color attributes now and whenever color is changed
            this.setColorAttributes();
            this.on('change:color', this.setColorAttributes, this);
            this.on('change:hidden change:cutoff', this.setVisibility, this);
        },
        setAndApprise: function() {
            var isSet = this.set.apply(this, arguments);
//            console.log('isSet', isSet);
            if(isSet) {
                this.trigger('changeApprisal', this);
            }
        },
        validate: function(attrs) {
            if(attrs.hasOwnProperty('highlighted')) {
                if(attrs.hasOwnProperty('visible') && attrs.visible) {
                    // do what you want w/ highlighting when it's visible
                } else {
                    // return error if this is not visible and you want to highlight
                    if(attrs.highlighted && this.getAttribute('visible')) {
                        return "alignments can't be highlighted when they are hidden or cutoff";
                    }
                }
            }
        }
    });
});