/**
 * Created by nmew on 8/14/14.
 */
define([
    'backbone',
    'handlebars'
], function(Backbone){
    return Backbone.View.extend({
        className: "alignmentGrid",

        template: "<table class='alignmentTable table table-bordered'><tbody>{{#each molecules}}" +
            "<tr><td><b>{{id}}</b></td>" +
            "{{#each points}}{{#if attributes.alignment}}{{#if attributes.alignment.attributes.visible}}<td style='{{#if attributes.alignment.attributes.highlighted}}font-weight: bold; border: 2px solid #555;{{/if}} background-color: {{attributes.alignment.attributes.lighterHexColor}};'>{{attributes.name}}</td>{{/if}}{{/if}}{{/each}}" +
            "</tr>" +
            "{{/each}}</tbody></table>",

        initialize: function() {
            // init listener on alignments
//            console.log('view init', this);
            this.debouncedRender = _.bind(_.debounce(this.render), this);
            this.model.alignments.forEach(function(a){
                this.listenTo(a, "change", this.debouncedRender);
            }, this);
            $(window).on("resize", this.debouncedRender);
            // compile the template
            this.compiledTemplate = Handlebars.compile(this.template);
        },

        render: function() {
//            console.log('AlignmentGrid rendering', this);
            var shallowMolecules = this.model.molecules.map(function(mol){
                // console.debug('points for ' + mol.id, mol.get('points'));
                var molVisiblePoints = mol.get('points').filter(function(point) {
                    // console.debug('point', point);
                    return point.has('alignment') && point.get('alignment').get('visible');
                });

                return {
                    id: mol.id,
                    points: molVisiblePoints,
                    visiblePoints: molVisiblePoints
                };
            });
            // console.debug('shallowMolCopy', shallowMolecules);

            this.el.innerHTML = this.compiledTemplate({
                molecules: shallowMolecules
            });

            var containerWidth = this.$el.width();
            var contentWidth = this.$('table.alignmentTable').width();
            // console.debug('containerWidth, contentWidth', containerWidth, contentWidth);
            if(contentWidth > containerWidth) {
//                _.each(shallowMolecules, function(shallowMol) {  });
                var visibleAls = this.model.alignments.where({visible: true});
                // console.debug('shallowMolecules', shallowMolecules);
                // console.debug('visible Als', visibleAls);
                var maxPerRow = Math.floor(shallowMolecules[0].visiblePoints.length * (containerWidth / contentWidth)) - 1;
                // var rows = Math.ceil(visibleAls.length / maxPerRow);
                var rowTemplates = [];
                // var i=0;
                while(shallowMolecules[0].visiblePoints.length > 0) {
                    // i++;
                    _.each(shallowMolecules, function(shallowMol){
                        shallowMol.points = _.first(shallowMol.visiblePoints, maxPerRow);
                        if(shallowMol.visiblePoints.length > maxPerRow) {
                            shallowMol.visiblePoints = _.rest(shallowMol.visiblePoints, maxPerRow);
                        } else {
                            shallowMol.visiblePoints = [];
                        }
                    });
                    // console.debug('split Row', i, shallowMolecules);
                    rowTemplates.push(this.compiledTemplate({
                        molecules: shallowMolecules
                    }));
                }
                this.el.innerHTML = rowTemplates.join('');
            }

            return this;
        },

        remove: function() {
            this.$el.empty();
            this.undelegateEvents();
            this.stopListening();
        }

    });
});