/**
 * Created by nmew on 8/28/14.
 */
define(['backbone', 'models/pose', 'handlebars'], function(Backbone, Pose) {
    return Backbone.View.extend({
        tagName: 'li',
        template: '<a href="#" class="viewItem{{#if active}} active{{/if}}">{{name}}</a>' +
            '<input type="text" class="editItem">' +
            '<div class="btn-group-vertical btn-group-xs editButtons editItem">' +
            '<button class="btn btn-default saveButton" title="OK">' +
            '<span class="glyphicon glyphicon-ok text-success" ></span>' +
            '</button>' +
            '<button class="btn btn-default cancelButton " title="Cancel">' +
            '<span class="glyphicon glyphicon-remove text-muted"></span>' +
            '</button>' +
            '</div>' +
            '<div class="btn-group-vertical btn-group-xs selectButtons viewItem">' +
            '<button class="btn btn-default editButton" title="Rename">' +
            '<span class="glyphicon glyphicon-pencil text-success"></span>' +
            '</button>' +
            '<button class="btn btn-default deleteButton" title="Delete Pose">' +
            '<span class="glyphicon glyphicon-trash text-danger"></span>' +
            '</button>' +
            '</div>' +
            '<div class="confirmationDialog hidden">' +
            '<div class="btn-group btn-group-sm">' +
            '<button type="button" class="btn btn-default btn-danger confirmDeleteButton">' +
            '<span class="glyphicon glyphicon-trash"></span> Delete</button>' +
            '<button type="button" class="btn btn-default text-primary cancelDeleteButton">' +
            'Cancel</button>' +
            '</div>' +
            '</div>',
        events: {
            "click a": "select",
            "click .saveButton": "save",
            "click .editButton": "edit",
            "click .cancelButton": "cancelEdit",
            "click .deleteButton": "toggleClearConfirmation",
            "click .cancelDeleteButton": "toggleClearConfirmation",
            "click .confirmDeleteButton": "clear",
            "click .confirmationDialog": "ignoreClicks",
            "click input": "ignoreClicks",
            "keyup input": "saveOrCancel"
        },
        initialize: function() {
            this.listenTo(this.model, "change", this.render);
            this.listenTo(this.model, "destroy", this.remove);
            this.compiledTemplate = Handlebars.compile(this.template);
        },
        render: function() {
            this.el.innerHTML = this.compiledTemplate(this.model.toJSON());
            return this;
        },
        remove: function() {
            this.undelegateEvents();
            Backbone.View.prototype.remove.apply(this, arguments);
        },
        select: function(e) {
            e.preventDefault();
            e.stopPropagation();
            this.trigger("selected", this.model);
        },
        save: function(e) {
            e.preventDefault();
            e.stopPropagation();
            var newName = this.$('input').val();
            if(newName.trim() !== '') {
                this.model.set('name', this.$('input').val());
                this.$el.toggleClass('edit', false);
            }
        },
        edit: function(e) {
            e.preventDefault();
            e.stopPropagation();
            var input = this.$('input');
            input.val(this.model.get('name'));
            this.$el.toggleClass('edit', true);
            input.focus();
            input.select();
        },
        cancelEdit: function(e) {
            e.preventDefault();
            e.stopPropagation();
            this.$el.toggleClass('edit', false);
        },
        toggleClearConfirmation: function(e) {
            e.preventDefault();
            e.stopPropagation();
            this.$('.confirmationDialog').toggleClass('hidden');
        },
        clear: function(e) {
            e.preventDefault();
            e.stopPropagation();
            this.model.destroy();
        },
        ignoreClicks: function(e) {
            e.stopPropagation();
        },
        saveOrCancel: function(e) {
            // if enter, save
            if (e.keyCode == 13) {
                this.save(e);
            }
            // if escape, cancel
            else if (e.keyCode == 27) {
                this.cancelEdit(e);
            }
        }
    });
});