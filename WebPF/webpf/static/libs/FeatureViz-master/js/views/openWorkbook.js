/**
 * Created by nmew on 9/11/14.
 */
define(['jquery', 'backbone', 'dataLoader', 'bootstrap'
], function($, Backbone, dataLoader) {
    return Backbone.View.extend({
        events: {
            'dragover div.dragDropZone': 'fileDragHover',
            'dragleave div.dragDropZone': 'fileDragHover',
            'drop div.dragDropZone': 'fileSelectHandler',
            'change input.fileselect': 'fileSelectHandler',
            'click a.exampleLink': 'linkSelectHandler',
            'hidden.bs.modal': 'fileDragReset'
        },
        initialize: function() {
            this.listenTo(this.model.vent, 'loaded:vizes', _.bind(function(){console.info('loaded:vizes caught');}, this));
            _.bindAll(this, 'updateModels', 'displayError');
        },
        render: function() {
//            var fileselect = this.el.querySelector(".fileselect");
//            var filedrag = this.el.querySelector(".dragDropZone");
            var fileselect = this.$(".fileselect");
            var filedrag = this.$(".dragDropZone");
//            fileselect.addEventListener("change", this.fileSelectHandler, false);
//            filedrag.addEventListener("dragover", this.fileDragHover, false);
//            filedrag.addEventListener("dragleave", this.fileDragHover, false);
//            filedrag.addEventListener("drop", this.fileSelectHandler, false);
            filedrag.on("click", function(){fileselect.click();});
            this.$el.modal({
                show: true/*,
                keyboard: false*/
            });
            return this;
        },
        fileDragHover: function(e) {
            e = e.originalEvent || e;
            if(e.stopPropagation && e.preventDefault) {
                e.stopPropagation();
                e.preventDefault();
                if(e.target.tagName.toUpperCase() === 'DIV') {
                    if(e.target.className.indexOf('hover') == -1 && e.type == "dragover") {
                        e.target.className = e.target.className + " hover";
                    } else if(e.target.className.indexOf('hover') !== -1 && e.type != "dragover") {
                        console.info(e.type, e);
                        e.target.className = e.target.className.replace(/ hover/g, "");
                    }
                }
            }
        },
        linkSelectHandler: function(e) {
            e = e.originalEvent || e;
            if(e.stopPropagation && e.preventDefault) {
                e.stopPropagation();
                e.preventDefault();
                $(e.target).addClass("loading");
                var link = e.target.href;
                dataLoader.loadByZipFileURL(link)['catch'](function(error){
                    console.error("promise error caught while loading zip from " + link, error);
                    this.displayError(error);
                    throw error;
                }).then(this.updateModels);
            }
        },
        fileSelectHandler: function(e) {
            e = e.originalEvent || e;
            // cancel event and hover styling
            this.fileDragHover(e);
            this.fileDragReset();
            $(e.target).addClass("loading");
            // fetch FileList object
            var files = e.target.files || e.dataTransfer.files;

            console.info('FileSelectHandler', e, files, e.target.result);

            if(files.length === 1 && dataLoader.safeToUnzip(files[0])) {
                this.fileDragReset();
                $(e.target).addClass("loaded");

                var theFile = files[0];

                // process all File objects
                var reader = new FileReader();
                var view = this;
                // Closure to capture the file information.
                reader.onload = function(e) {
                    try {
                        // update the page with the molecule defs
                        dataLoader.loadByZipFile(e.target.result)['catch'](function(error){
                            console.error("promise error caught", error);
                            view.displayError(error);
                        }).then(view.updateModels);
                    } catch(er) {
                        console.error("Error reading " + theFile.name + " : " + er.message);
                        view.displayError(er);
                    }
                };
                // read the file
                reader.readAsArrayBuffer(theFile);
            } else {
                var message = "can't read multiple files.";
                console.error(message);
                this.fileDragReset();
                this.displayError({message:message});
            }
        },
        fileDragReset: function(e) {
            var el = this.$el.find('.dragDropZone');
            el.removeClass('hover loaded error');
        },
        updateModels: function(model) {
            if(model) {
                console.info('updateModels', arguments);
                console.info('modelbeforeload', this.model);
                this.model.molecules = model.molecules;
                this.model.alignments = model.alignments;
                this.model.featureVizSettings = model.featureVizSettings;
                this.model.poses = model.poses;
                console.info('modelafterload', this.model);
                this.model.vent.trigger('updateModels');
                // hide modal after a little bit
                _.delay(this.$el.modal.bind(this.$el), 0, 'hide');
            } else {
                console.warn('updateModels: Undefined or null model.');
            }
        },
        displayError: function(error) {
            this.fileDragReset();
            var addClass = this.$(".dragDropZone").addClass.bind(this.$(".dragDropZone"));
            _.delay(addClass, 500, "error");
        }
    });
});