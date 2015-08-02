/**
 * Created by nmew on 8/27/14.
 */
define([
    'backbone',
    'collections/poses',
    'views/poseMenuItem',
    'views/moleculeVizualizer',
    'views/alignmentGrid',
    'kabsch'
], function(Backbone, Poses, PoseMenuItem, MolViz, AlignmentGrid, Kabsch) {

    function matrixToJmolScript(matrix) {
        var i, script = '[';
        for(i=0; i<matrix.length; i++) {
            if(i!=0) {
                script += ',';
            }
            script += '[' +
                matrix[i].toString().replace(/,/g, ' ') +
                ']';
        }
        return script + ']';
    }

    return Backbone.View.extend({
        syncButtonTemplate: '<button type="button" class="btn btn-default btn-xs syncButton" title="" data-original-title="Synchronize Mouse Movements"><span class="glyphicon glyphicon-link"></span></button>',
        events: {
            "click #savePoseButton": "savePose",
            "click #autoPoseButton": "autoPose",
            "click .syncButton": "toggleSync",
            "hide.bs.dropdown .poseDropDown": "cancelAllPoseEdits"
        },
        initialize: function() {
            this.vent = this.model.vent;
            this.renderSettings = this.model.featureVizSettings;
            this.molecules = this.model.molecules;
            this.alignments = this.model.alignments;
            this.poses = this.model.poses;
            this.vizes = [];
            this.$vizGrid = this.$('#vizGrid');
            this.$poseMenu = this.$('.poseMenu');
            this.listenTo(this.poses, 'add', this.addPoseMenuItem);
            this.listenTo(this.vent, 'sliderChange:scoreCutoff', this.synchronousVizUpdate);
            this.listenTo(this.vent, 'saveImages', this.synchronousImageSave);
        },
        render: function() {
            console.info('rendering moleculevizualizersfcontainer', this);

            // animate show
            this.$el.addClass('rendered');

            // create table under jmol vizes
            this.alignmentGrid = new AlignmentGrid({
                el: this.$el.find('#alignmentGrid'),
                model: {
                    molecules: this.molecules,
                    alignments: this.alignments
                }
            }).render();

            // add passed in poses to menu
            this.poses.forEach(function(pose) {
                this.addPoseMenuItem(pose);
            }, this);

            // clear old viz grid
            this.$vizGrid.empty();

            // create possed in molecules
            this.molecules.forEach(function(molecule, index) {
//                console.log('vizcontainer', this.el);
                var container = document.createElement('div');
                this.$vizGrid.append(container);
                var viz = new MolViz({
                    el: container,
                    vent: this.vent,
                    molecule: molecule,
                    renderSettings: this.renderSettings
                }).render();
                this.listenTo(viz, "loaded", this.onVizLoad);
                this.listenTo(viz, "change:locked", this.cancelSync);
                this.vizes.push(viz);
                // add sync buttons between molecules
                if(index < this.molecules.length - 1) {
                    var centerButtonsContainer = document.createElement('div');
                    centerButtonsContainer.className = 'centerButtonsContainer';
                    // sync mousemovements button
                    centerButtonsContainer.innerHTML = this.syncButtonTemplate;
                    this.$vizGrid.append(centerButtonsContainer);
                }
            }, this);

            // add tooltip to sync buttons
            this.$('.syncButton').tooltip();

            // add AutoPose info popover
            this.$('.autoPoseInfo').popover({
                container: 'body',
                placement: 'right',
                trigger: 'hover',
                html: true,
                delay: { show: 100, hide: 800 },
                title: 'How <span class="glyphicon glyphicon-flash"></span> Auto Pose Works:',
                content: "If neither molecules are locked (<span class='glyphicon glyphicon-lock'></span>):" +
                    "<ol><li>Center the left molecule around the selected/highlighted alignments</li><li>Rotate and zoom it to a default position containing all highlighted alignments</li><li>Rotate and zoom the right molecule to fit the orientation of the alignments in the left molecule</li></ol>" +
                    "If only one of the molecules are locked (<span class='glyphicon glyphicon-lock'></span>):" +
                    "<ol><li>Rotate and zoom the unlocked molecule to fit the orientation of the selected/highlighted alignments in the locked molecule</li></ol>" +
                    "The <a href='http://en.wikipedia.org/wiki/Kabsch_algorithm' target='_blank'>Kabsch algorithm</a> is used to calculate the optimal rotation that minimizes RMSD. No weight is given to the alignment, all alignments are treated equally."
            });

            return this;
        },
        /**
         * This seems to be better at preventing page redraw issues than
         * allowing each to listen to an event and render close to simultanously.
         */
        synchronousVizUpdate: function() {
            _.forEach(this.vizes, function(molViz) {
                molViz.updateChangedPoints();
            });
        },
        synchronousImageSave: function(options) {
            _.forEach(this.vizes, function(molViz, index, list) {
                if(options.format === 'PNG') {
                    console.info(Jmol.scriptWait(molViz.applet,
                            'delay 1; set refreshing false; ' +
                            'set hermiteLevel ' + this.renderSettings.get('export_hermiteLevel') + '; ' +
                                'set antialiasImages ON; set imageState FALSE; write image ' +
                            molViz.applet._width * options.size + ' ' +
                            molViz.applet._height * options.size + ' PNG ' +
                            molViz.molecule.id + '_' +
                            molViz.molecule.get('points').first().get('ligand') + '.png; ' +
                                'set hermiteLevel ' +
                                (this.renderSettings.get('hq') ? this.renderSettings.get('hq_hermiteLevel') : this.renderSettings.get('lq_hermiteLevel')) + '; ' +
                                'set refreshing true;'));
                } else {
                    console.info(Jmol.scriptWait(molViz.applet,
                            'delay 1; set imageState FALSE; set refreshing false; ' +
                            'set hermiteLevel ' + this.renderSettings.get('export_hermiteLevel') + '; ' +
                            'write POVRAY ' +
                            molViz.molecule.id + '_' +
                            molViz.molecule.get('points').first().get('ligand')+ '.pov; set hermiteLevel ' +
                                (this.renderSettings.get('hq') ? this.renderSettings.get('hq_hermiteLevel') : this.renderSettings.get('lq_hermiteLevel')) + '; ' +
                                '; set refreshing true;'));
                }
                molViz.vent.trigger('imagesSaveUpdate',  { complete: index+1, total: list.length });
            }, this);
            console.info('triggering images saved');
            this.vent.trigger('imagesSaved');
        },
        autoPose: function(event) {
            // if their not both locked
            if(!_.every(this.vizes, function(molViz) { return molViz.locked; })) {
                // get highlighted alignments
                var alignmentsToAlign = this.alignments.where({highlighted: true});
                if(alignmentsToAlign.length > 1) {
                    // pindex is set to right (1) viz by default
                    var P = [], Q = [], pi = 1, qi = 0;
                    // but if it's locked, then flip them
                    if (this.vizes[1].locked) {
                        qi = 1;
                        pi = 0;
                    }
                    // get the xyz of each highlighted point in P and Q
                    _.forEach(alignmentsToAlign, function (alignment) {
                        var points = alignment.get('points');
                        P.push([+points[pi].get('x'), +points[pi].get('y'), +points[pi].get('z')]);
                        Q.push([+points[qi].get('x'), +points[qi].get('y'), +points[qi].get('z')]);
                    });
                    console.info({P: P.toString(),Q:Q.toString()});
                    // center the points and get center points
                    var pCenter = Kabsch.centerPoints(P);
                    var qCenter = Kabsch.centerPoints(Q);
                    console.info('Pc', pCenter);
                    console.info('Qc', qCenter);
                    // get rotation matrix to fit P onto Q
                    var fit = Kabsch.fit(P, Q);

                    // if both vizes are unlocked
                    if(_.every(this.vizes, function(molViz) { return !molViz.locked; })) {
                        // set best rotation on Q first
                        this.vizes[qi].setBestRotation(true);
                        var centerScript = "center {" +
                            qCenter.toString().replace(/,/g, ' ') + "};";
                        Jmol.scriptWait(this.vizes[qi].applet, centerScript);
                    }

                    // get Q's orientation
                    var orientation = this.vizes[qi].getRotationAboutFront();
                    // left or right handed rotation matrix
    //                var rotationMatrix = fit.rotationCorrected ? numeric.transpose(fit.rotationMatrix) : fit.rotationMatrix;
                    var rotationMatrix = numeric.transpose(fit.rotationMatrix);
                    var rotationScript = "set refreshing false;" +
                        "moveto 0 back;" +
                        "center {" + pCenter.toString().replace(/,/g, ' ') + "};" +
                        "rotate " +
                        matrixToJmolScript(rotationMatrix) + ";" +
                        "center {" + pCenter.toString().replace(/,/g, ' ') + "};";

                    var currentWindowYAxisScript = "q = quaternion();" +
                        "rotVector = q%{0 1 0};" +
                        "relativeRotVector = @rotVector - {" + pCenter.toString().replace(/,/g, ' ') + "};";

                    var orientLikeQ = "rotate y 180;" + orientation +";";

                    rotationScript +=
    //                currentWindowYAxisScript +
                        orientLikeQ +
                        "set refreshing true;";

                    this.vizes[pi].runScript(rotationScript);

                    console.info(fit);

                    if(event.currentTarget) {
                        var $button = $(event.currentTarget);
                        $button.addClass('complete');
                        event.currentTarget.blur();
                        setTimeout(function(){$button.removeClass('complete');}, 200);
                    }
                } else {
                    // can't align just one point
                    if(event.currentTarget) {
                        var $button = $(event.currentTarget);
                        $button.addClass('error');
                        event.currentTarget.blur();
                        setTimeout(function(){$button.removeClass('error');}, 400);
                    }
                }
            } else {
                // can't align when both are locked
                if(event.currentTarget) {
                    var $button = $(event.currentTarget);
                    $button.addClass('error');
                    event.currentTarget.blur();
                    setTimeout(function(){$button.removeClass('error');}, 400);
                }
            }
        },
        savePose: function(poseName) {
            var buttonClick =  !_.isString(poseName);

            this.poses.create({
                name: buttonClick ? 'Pose ' + (this.poses.length + 1) : poseName,
                scripts: _.map(this.vizes, function(molViz){ return molViz.getPoseScript(); })
            });
            if(buttonClick) {
                var event = poseName;
                var $button = $(event.currentTarget);
                $button.addClass('complete');
                event.currentTarget.blur();
                setTimeout(function(){$button.removeClass('complete');}, 200);
            }
        },
        restorePose: function(pose) {
            // loop through pose scripts and run on each viz
            for(var i=0; i<pose.get('scripts').length; i++) {
                this.vizes[i].runScript(pose.get('scripts')[i]);
            }
        },
        addPoseMenuItem: function(pose) {
            // create new poseview and add to menu
            console.info('addingposemenuitem', pose);
            var pMI = new PoseMenuItem({model: pose});
            this.listenTo(pMI, "selected", this.restorePose);
            this.$poseMenu.append(pMI.render().el);
        },
        cancelAllPoseEdits: function() {
            $('li', this.$poseMenu).removeClass('edit');
        },
        cancelSync: function() {
            var button = this.$('.syncButton')[0];
            var synced = button.className.indexOf('primary') > -1;
            if(synced) {
                this.toggleSync({currentTarget: button});
                this.flashRedButton(button);
            }
        },
        toggleSync: function(e) {
            var button = e.currentTarget;
            var synced = button.className.indexOf('primary') > -1;
            if(synced) {
                // unsync
                this.vizes[0].runScript('sync * off;');
                button.blur();
                $(button).removeClass('btn-primary');
            } else {
                // if all are unlocked
                if(_.every(this.vizes, function(molViz) { return !molViz.locked; })) {
                    // sync
                    this.vizes[0].runScript('sync * on; sync * "set syncMouse true";');
                    button.blur();
                    $(button).addClass('btn-primary');
                } else {
                    // flash red
                    this.flashRedButton(button);
                }
            }
        },
        flashRedButton: function(button) {
            $(button).addClass('btn-danger');
            button.blur();
            setTimeout(function(){$(button).removeClass('btn-danger');}, 300);
        },
        onVizLoad: function() {
            if(_.every(this.vizes, function(molViz) { return molViz.loaded; })) {
                // if there are no poses set, add a default pose
                this.vent.trigger("loaded:vizes");
                if(this.poses.length <= 0) {
                    this.savePose("Default Pose");
                }
            }
        },
        remove: function() {
            // animate hide
            this.$el.removeClass('rendered');
            // kill alignmentGrid
            this.alignmentGrid.remove();
            // kill poses
            this.model.poses.invoke('destroy');
//            _.each(_.clone(this.poses), function(model) {
//                model.destroy();
//            });
            this.poses = [];
            this.$poseMenu.empty();
            // kill vizes
            _.forEach(this.vizes, function(molViz) {
                molViz.remove();
            });
            this.vizes = [];
            this.$vizGrid.empty();
            // kill jmol applets, globals included
            _.forEach(_.keys(Jmol._applets), function(key) {
                delete window[key];
            });
            Jmol._applets = {};
            // remove all listeners
            this.undelegateEvents();
            this.stopListening();
        }
    });
});
