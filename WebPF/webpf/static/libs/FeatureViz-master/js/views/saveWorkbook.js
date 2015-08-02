/**
 * Created by nmew on 9/14/14.
 */
define(['backbone', 'dataLoader', 'bootstrap'], function(Backbone, dataLoader) {
    return Backbone.View.extend({
        events: {
            'click .saveWorkBookButton': 'saveToDisk'
        },
        initialize: function(options) {
            this.button = options.button;
        },
        render: function() {
            if(this.button) {
                this.button.removeClass('disabled');
            }
            this.$el.find('input#workbookNameInput').keydown(function(event){
                if(event.keyCode == 13) {
                    event.preventDefault();
                }
            });
            return this;
        },
        saveToDisk: function() {
            dataLoader.saveToDisk(this.model, this.$el.find('input#workbookNameInput').get(0).value);
            this.$el.modal('hide');
        }
    });
});