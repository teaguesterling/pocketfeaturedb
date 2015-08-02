/**
 * Created by nmew on 9/14/14.
 */
define(['backbone', 'jmol'], function(Backbone) {
    return Backbone.View.extend({
        template: '<p class="lead">Select a format to export images below. You will be prompted for image file name after clicking the "Save Images" button.</p>' +
            '<form class="form-inline" role="form">' +
            '<div class="radio"><label><input type="radio" name="optionsRadios" id="pngRadio" value="PNG" checked> <strong>PNG</strong></label></div> ' +
//            '<div class="checkbox"><label><input type="checkbox" checked><strong>PNG</strong></label></div>' +
            '<fieldset class="form-group pngInlineForm"><div class="input-group">' +
            '<div class="input-group-addon">Resolution:</div>' +
            '<select class="form-control sizeSelect">' +
            '<option value="2">650x490 (2x)</option>' +
            '<option value="3">975x735 (3x)</option>' +
            '<option value="4">1300x980 (4x)</option>' +
            '<option value="5">1625x1225 (5x)</option>' +
            '<option value="6">1950x1470 (6x)</option>' +
            '</select>' +
            '</div></fieldset><br><br>' +
            '<div class="radio"><label><input type="radio" name="optionsRadios" id="povrayRadio" value="POVRAY"> <strong>POV-Ray</strong></label>' +
            '<label class="text-danger"><span class="glyphicon glyphicon-asterisk"></span> Bug: Chrome crashes and Safari will not save files. Try Firefox for now.</label>' +
            '</label></div>' +
            '</form><br>',
        events: {
            'click .saveImagesButton': 'saveImages',
            'click input[type="radio"]': 'toggleForm'
        },
        initialize: function(options) {
            this.button = options.button;
            this.listenTo(this.model.vent, 'imagesSaved', this.hideModal);
            this.listenTo(this.model.vent, 'imagesSaveUpdate', this.updateProgress);
        },
        render: function() {
            if(this.button) {
                this.button.removeClass('disabled');
            }
            this.$('.moleculeSelectButtons').html(this.template);
            return this;
        },
        saveImages: function() {
            console.log('save images', this.$('#pngRadio').is(":checked"));
            // show load bar
            this.updateProgress({complete: 0, total: this.model.molecules.length});
            this.$('.progress').removeClass('hidden');

            var size = 8;
            var format = '';
            if(this.$('#pngRadio').is(":checked")) {
                format = 'PNG';
                size = this.$('.sizeSelect option:selected').val();
            } else {
                format = 'POVRAY';
            }
            // call jmol save images
            this.model.vent.trigger('saveImages', {format: format, size: size});
            // hide load bar once saved
//            this.model.vent.on('imagesSaved', this.hideModal, this);
        },
        toggleForm: function() {
            if(this.$('#pngRadio').is(":checked")) {
                this.$('.pngInlineForm').removeAttr('disabled');
            } else {
                this.$('.pngInlineForm').attr('disabled','disabled');
            }
        },
        updateProgress: function(progress) {
            this.$('.progress-bar.active').width(100/progress.total + '%');
            this.$('.progress-bar.complete').width(100*progress.complete/progress.total + '%');
        },
        hideModal: function() {
            this.$('.progress').addClass('hidden');
            this.$el.modal('hide');
        },
        remove: function() {
            if(this.button) {
                this.button.addClass('disabled');
            }
            this.hideModal();
            this.$('.moleculeSelectButtons').empty();
            this.undelegateEvents();
            this.stopListening();
        }
    });
});