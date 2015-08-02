/**
 * Created by nmew on 8/29/14.
 */
define(['backbone'], function(Backbone){
    return Backbone.Model.extend({
        set: function(key, val, options) {
            if (typeof key === 'object') {
                attrs = key;
                options = val;
            } else {
                (attrs = {})[key] = val;
            }

            options || (options = {});

            if(options.ui) {
                options.silent = true;
            }

            console.log('setting', attrs, options);
            var didSet = Backbone.Model.prototype.set.call(this, attrs, options);


            if(didSet && options.ui) {
                _.each(_.keys(attrs), function(attr){
                    if(this.hasChanged(attr)) {
//                        console.log('uiChange:'+attr, attrs);
                        this.trigger('uiChange:'+attr, this, attrs[attr], options);
                    }
                }, this);
            }

            return didSet;
        }
    });
});