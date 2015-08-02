/**
 * Created by nmew on 8/27/14.
 */
// todo: jmol onload fire loaded
define([
    'underscore',
    'backbone',
    'jmol',
    'handlebars'
], function(_, Backbone){
    return Backbone.View.extend({
        template: '<div><h1>{{title}}</h1><label class="checkbox-inline moleculeLockCheckbox"><input type="checkbox" {{#if locked}}checked="checked"{{/if}}><span class="glyphicon glyphicon-lock"></span> Lock Pose</label></div><div class="vizBody"></div>',
        className: "vizContainer",
        applet: null,
        appletId: null,
        molecule: null,
        loaded: false,
        title: false,
        locked: false,
        renderSettings: null,
        jmolDefaultInfo: {
            width: 325,
            height: 425,
            zIndexBase: 200,
            debug: false,
            color: "0xFFFFFF",
            addSelectionOptions: false,
            use: "HTML5",   // JAVA HTML5 WEBGL are all options
            // todo: can we make these relative?
            j2sPath: "js/lib/jmol-14.0.13/jsmol/j2s", // this needs to point to where the j2s directory is.
            isSigned: true,
            disableJ2SLoadMonitor: true,
            disableInitialConsole: true,
            allowJavaScript: true
//            console: "none", // default will be jmolApplet0_infodiv, but you can designate another div here or "none"
        },
        events: {
            "change input": "toggleLock"
        },
        initialize: function(options) {
            // bind models and event bus
            _.extend(this, _.pick(options, 'vent', 'molecule', 'renderSettings'));
            // bind our methods
            _.bindAll(this, 'renderMolecule', 'runScript', 'jmolOnLoad', 'updateLigand', 'updatePoint','updateAllPoints' ,'updateChangedPoints' ,'queueChangedPointsForUpdate', 'updateZSlabAndDepth', 'updateHQ', 'getRotationAboutFront', 'setBestRotation');
            // compile the template
            this.compiledTemplate = Handlebars.compile(this.template);
            // title
            this.title =  this.molecule.id + "/"+ this.molecule.get('points').first().get('ligand');

            // init point change listeners
            this.debouncedUpdateChangedPoints || (this.debouncedUpdateChangedPoints = _.debounce(this.updateChangedPoints));

            this.molecule.get('points').forEach(function(point){
                if(point.get('alignment')) {
                    this.listenTo(point.get('alignment'), "change", this.queueChangedPointsForUpdate);
                    this.listenTo(point.get('alignment'), "changeApprisal", this.debouncedUpdateChangedPoints);
                }
            }, this);
            this.listenTo(this.renderSettings, "change:slab change:zSlab change:zDepth", this.updateZSlabAndDepth);
            this.listenTo(this.renderSettings, "change:ballScale", this.updateAllPoints);
            this.listenTo(this.renderSettings, "change:hq", this.updateHQ);

            // init ligand script
            this.listenTo(this.vent, 'ligandScript', this.runLigandScript);
            this.listenTo(this.renderSettings, "change:ligandDisplayValue", this.updateLigand);
            // listen to new molecule script
            this.listenTo(this.vent, 'moleculeScript', this.runScript);

        },
        render: function() {
            this.appletId = "jmolApplet_" + this.molecule.cid;  // set applet id
            this.el.className += this.className;                // className on contianer
            this.el.innerHTML = this.compiledTemplate(this);    // checkbox, title, containers
            this.renderMolecule();                              // JMol init + html
            return this;
        },
        remove: function() {
            this.undelegateEvents();
            Backbone.View.prototype.remove.apply(this, arguments);
        },
        renderMolecule: function () {
            // set jmol on load callback
            this.jmolDefaultInfo.readyFunction = this.jmolOnLoad;

            // script to load pdb
            var loadScript = typeof this.molecule.get('pdb') === 'string' ?
                "load ASYNC " + this.molecule.get('pdb') + "; " :
                'data "model example"\n' + this.molecule.get('pdb').asText() + '\n end "model example"; show data; ';

            // script to render ligand properly
            var descript = this.molecule.get('points').first().get('description').split('_');
            var ligandScript = "subset within(3, ["+descript[3]+"]:"+descript[1]+"); zoom {*} 0; subset all; " +
                "select ["+descript[3]+"]:"+descript[1]+"#"+descript[2]+"; " +
                this.renderSettings.get('ligandDisplayRepresentation') + " " + this.renderSettings.get('ligandDisplayValue') + ";" +
                "color cpk;";

            // set script to run on jmol applet/canvas creation
            this.jmolDefaultInfo.script = "set refreshing false; set showFrank false; set allowGestures false;  " +
                "set drawHover ON; set drawPicking ON; " +
                "set antialiasDisplay " + this.renderSettings.get('hq') + "; " +
                loadScript +
                // set sheetSmoothing 0 creates wavy sheets, with the ribbon or trace going directly through the alpha carbons.
                // The default is set sheetSmoothing 1, which produces a more averaged, smoother (standard) ripple
                "SET sheetSmoothing 1; " +
                // When set FALSE, translucent obects are not translucent to each other, creating an unreal but
                // possibly desired effect similar to the default PyMOL setting transparency_mode 1.
                "SET translucent false; " +
                // hermiteLevel:
                //  Positive values produce more rounded but slower to render shapes, but only when the model is not in motion.
                //  Negative numbers produce the same, but also while rotating
                "SET hermiteLevel " + (this.renderSettings.get('hq') ? this.renderSettings.get('hq_hermiteLevel') : this.renderSettings.get('lq_hermiteLevel')) + "; " +
                // spacefill: Renders selected atoms as shaded spheres
                "spacefill off; " +
                // turn cartoon on for everything
                "wireframe off; cartoon on; " +
                "color cartoons [xdedede]; color cartoons translucent 0.50; " +
                "SET cartoonsfancy " + this.renderSettings.get('hq') + "; " +
                "set ribbonborder true; " +
                // turn cartoon off for protein then turn on whatever is selected in render settings
                "select {protein}; cartoon off; " + this.renderSettings.get('moleculeDisplayRepresentation') + " on; " +
                "slab on; zShade = true; zshadePower = 2; " +
                // An ambientPercent value of 0 creates an effect of a spotlight on a stage;
                // a value of 100 removes the shadow entirely, creating a flat, nonrealistic effect.
                "ambientPercent = 50; " +
                "set zSlab " + this.renderSettings.get('zSlab') + "; " +
                "set zDepth " + this.renderSettings.get('zDepth') + ";" +
                "set slab " + this.renderSettings.get('slab') + "; " +
                'platformSpeed = 4; moveto 0 back; set refreshing TRUE;' +
                ligandScript;
            var html = Jmol.getAppletHtml(this.appletId, this.jmolDefaultInfo);
//            this.el.querySelector('.vizBody').innerHTML = html;
            this.$el.find('.vizBody').html(html);
            this.applet = window[this.appletId];
        },
        toggleLock: function() {
            var vizContainer = this.el.querySelector(".vizBody");
            var lockedClass = ' locked';
            this.locked = !this.locked;
            if(this.locked) {
                vizContainer.className += lockedClass;
                setTimeout(function(){Jmol.script(this.applet, "set refreshing false;");}.bind(this), 5);
            } else {
                var regEx = new RegExp(lockedClass,'g');
                vizContainer.className = vizContainer.className.replace(regEx, '');
                this.runScript('set refreshing true;');
            }
            this.trigger('change:locked', this.locked);
        },
        updatePoint: function(point) {
            console.debug('updatePoint', arguments);
            this.runScript(this.getRenderPointScript(point) + "; set drawHover ON; set drawPicking ON;");
        },
        queueChangedPointsForUpdate: function(alignment) {
            this.queuedPointsToUpdate || (this.queuedPointsToUpdate = []);
            _.each(alignment.get('points'), function(point){
                if(point.get('molecule').id === this.molecule.id) {
                    this.queuedPointsToUpdate.push(point);
                    console.debug('queueing ', point.get('description'));
                }
            }, this);
        },
        updateChangedPoints: function(){
            console.debug('updateChangedPoints');
            if(this.queuedPointsToUpdate && this.queuedPointsToUpdate.length > 0) {
                var pointScripts = _.reduce(_.uniq(this.queuedPointsToUpdate), function(memo, point){
//                    console.debug('updating ', point.get('description'));
                    return memo + this.getRenderPointScript(point);
                }, ' ', this);
//                console.debug(pointScripts);
                this.queuedPointsToUpdate = [];
                this.runScript(pointScripts + "; set drawHover ON; set drawPicking ON;");
            }
        },
        updateAllPoints: function() {
            // script to render aligned points
            var pointScripts = this.molecule.get('points').reduce(function(memo, point){
                return memo + this.getRenderPointScript(point);
            }, ' ', this);
            this.runScript(pointScripts + "; set drawHover ON; set drawPicking ON;");
        },
        updateZSlabAndDepth: function() {
            this.runScript("slab on; set slab " + this.renderSettings.get('slab') +
                "; set zSlab " + this.renderSettings.get('zSlab') +
                "; set zDepth " + this.renderSettings.get('zDepth') + ";");
        },
        runLigandScript: function(script) {
            this.runScript('select ' + this.getLigandAtomExpression() + script);
        },
        updateLigand: function() {
            this.runScript(this.getLigandScript());
        },
        updateHQ: function() {
            if(this.renderSettings.get('hq')) {
                this.runScript("set antialiasDisplay true; set cartoonsfancy false; " +
                    "set hermiteLevel " + this.renderSettings.get('hq_hermiteLevel'));
            } else {
                this.runScript("set antialiasDisplay false; set cartoonsfancy true; " +
                    "set hermiteLevel " + this.renderSettings.get('lq_hermiteLevel'));
            }
        },
        getRenderPointScript: function(point) {
            if(point.get('alignment')) {
                var radius = point.get('alignment').get('visible') ?
                    this.renderSettings.get('ballScale') * point.get('alignment').get('score') : 0;

                var translucence = point.get('alignment').get('highlighted') ?
                    0 : 0.7;

                return "isosurface " + point.get('name') + " center {" +
                    point.get('x') + " " +
                    point.get('y') + " " +
                    point.get('z') + "} sphere " + radius + ";" +
                    "color $" + point.get('name') +
                    " TRANSLUCENT " + translucence + "  {" + point.get('alignment').get('color').rgb() + "};";
            } else {
                return '';
            }
        },
        getAtomSelectionScriptAroundPoint: function(point, radius) {
            if(point.get('alignment')) {
                var radius = radius || 1.5;
                return " select " +
                    (point.get('alignment').get('highlighted') ?
                    "ADD" : "REMOVE") +
                    " WITHIN(" + radius + ", {" +
                    point.get('x') + " " +
                    point.get('y') + " " +
                    point.get('z') + "});";
            } else {
                return '';
            }
        },
        getLigandScript: function() {
            return "select " + this.getLigandAtomExpression() + ";" +
                this.renderSettings.get('ligandDisplayRepresentation') + " " +
                this.renderSettings.get('ligandDisplayValue') + ";" +
                "color cpk;";
        },
        getLigandAtomExpression: function() {
            var descript = this.molecule.get('points').first().get('description').split('_');
            return "["+descript[3]+"]:"+descript[1];
        },
        getPoseScript: function() {
            var orientation = Jmol.scriptWait(this.applet, "show MOVETO;").replace("moveto 1.0", "moveto 0");
            return orientation.slice(orientation.indexOf("moveto 0 "));
        },
        getRotationAboutFront: function() {
            var orientation = Jmol.scriptWait(this.applet, "show orientation; ");
            // add rotation radius
            var rotRadiusScript = Jmol.scriptWait(this.applet, "show rotationRadius;");
            var radiusLocation = rotRadiusScript.indexOf("rotationRadius = ");
            rotRadiusScript = rotRadiusScript.slice(radiusLocation);
            // add rotation radius if neccessary
            if (orientation.indexOf('set rotationRadius') === -1) {
                orientation += rotRadiusScript + "; ";
            }
            // clean up
            orientation = orientation.replace(/\n/g," ");
            var isRotated = orientation.indexOf("; rotate ");
            return isRotated ?
                orientation.slice(orientation.indexOf("; rotate ")).replace(";", "") :
                orientation.slice(orientation.indexOf(" zoom "));
        },
        setBestRotation: function(synchronous) {
            if(!synchronous) {
                this.runScript("rotate best;");
            } else {
                Jmol.scriptWait(this.applet, "rotate best;");
            }
        },
        runScript: function(script) {
            console.debug('Applet: ' + this.appletId + ' running script: ', script);
            Jmol.script(this.applet, script);
            if(this.locked) {
                Jmol.script(this.applet, "set refreshing true; delay 0.1; set refreshing false;");
            }
        },
        jmolOnLoad: function(applet) {
            this.applet = applet;
            this.updateAllPoints();
            this.loaded = true;
            this.trigger("loaded", this);
        }
    });
});