/**
 * Created by nmew on 8/14/14.
 */
/**
 * Created by nmew on 8/14/14.
 */
define([
    'jquery',
    'backbone',
    'chroma',
    'colorSchemes',
    'spectrum',
    'handlebars'
], function($, Backbone, chroma, colorSchemes){
    var colorBallStyle = 'background-color: {{attributes.darkerHexColor}};' +
        'background-image: repeating-linear-gradient(180deg, {{attributes.lighterHexColor}}, {{attributes.hexColor}}, {{attributes.darkerHexColor}});' +
        'filter: progid:DXImageTransform.Microsoft.gradient(GradientType=0, StartColorStr={{attributes.lighterHexColor}}, EndColorStr={{attributes.darkerHexColor}});';
    var columnTemplates = {
        alignmentIndex: {
            order: 0,
            template: "<td class='noHoverHighlight'>{{alignmentIndex}}</td>"
        },
        selection: {
            order: 1,
            template: "<td class='noHoverHighlight'><input type='checkbox' {{#if visible}}CHECKED{{/if}}/></td>"
        },
        visibility: {
            order: 1,
            template: "<td class='toggleVisibility noHoverHighlight {{#unless attributes.cutoff}}withinCutoff{{/unless}}'><span class='glyphicon {{#if attributes.visible}}glyphicon-eye-open{{else}}glyphicon-eye-close{{/if}}' ></span></td>"
//            template: "<td class=\"toggleVisibility noHoverHighlight {{#if attributes.cutoff '<' ../../featureVizSettings.attributes.alignmentScoreCutoffUI}}withinCutoff{{/if}}\"><span class='glyphicon {{#if attributes.visible}}glyphicon-eye-open{{else}}glyphicon-eye-close{{/if}}' ></span></td>"
        },
        color: {
            order: 2,
            template: "<td class='colorBall noHoverHighlight {{#unless attributes.cutoff}}withinCutoff{{/unless}}'><div class='colorBall-container'><div data-color='{{attributes.hexColor}}' data-alignmentIndex='{{@index}}' id='colorBall_{{@index}}' class='colorBall' style='" + colorBallStyle + "'><span class='arrow'>▼</span></div></div></td>"
        }
    };
    var tableTemplate   = "<table class='table-condensed table-striped table table-hover'><thead><tr>" +
//        "<th></th>" +
        "<th></th>" +
        "<th class='colorSchemePicker'><span class='glyphicon glyphicon-th'></span><span class='caret'></span></th>" +
        "{{#each molecules.models}}<th>{{id}}</th>{{/each}}" +
        "<th>Similarity</th>" +
        "</tr></thead>" +
        "<tbody></tbody></table>";

    var tableBodyTemplate = "{{#each alignments.models}}" +
        "<tr {{#if attributes.highlighted}}class='info'{{/if}} data-alignmentindex='{{@index}}'>" +
//            columnTemplates.selection.template +
        columnTemplates.visibility.template +
        columnTemplates.color.template +
        "{{#each attributes.points}}<td class='toggleHighlight'>{{attributes.name}}</td>{{/each}}" +
        "<td class='toggleHighlight'>{{attributes.score}}</td>" +
        "</tr>" +
        "{{/each}}";

    var ColorSchemeOption = Backbone.View.extend({
        attributes: {
            'class': "ramp",
            'data-toggle': "tooltip",
            'data-placement': "bottom"
        },
        render: function(parentEl) {
            this.$el.attr('title', this.model.schemeKey);
            this.uniqueClass = 'ColorSchemeOption_' + this.model.schemeKey;
            this.$el.addClass(this.uniqueClass);
            this.$el.html(
                '<svg width="15" height="75">' +
                '<rect fill="' + this.model.colors[0] + '" width="15" height="15" y="0"></rect>' +
                '<rect fill="' + this.model.colors[1] + '" width="15" height="15" y="15"></rect>' +
                '<rect fill="' + this.model.colors[2] + '" width="15" height="15" y="30"></rect>' +
                '<rect fill="' + this.model.colors[3] + '" width="15" height="15" y="45"></rect>' +
                '<rect fill="' + this.model.colors[4] + '" width="15" height="15" y="60"></rect>' +
                '</svg>');

            parentEl.on('click', 'div.' + this.uniqueClass, _.bind(this.select, this));
            return this;
        },
        select: function(event) {
            event.stopPropagation();
            this.trigger("selected", this.model);
        }
    });


    return Backbone.View.extend({
        className: "alignmentTable",

        template: tableTemplate,
        bodyTemplate: tableBodyTemplate,

        events: {
            "click .toggleVisibility": "toggleVisibility",
            "click .toggleHighlight": "toggleHighlight"
        },

        initialize: function() {
            // bind setHighlight to this
            _.bind(this.setHighlight, this);
            // init listener on alignments
//            console.log('view init', this);
            this.attributes.alignments.forEach(function(a){
                this.listenTo(a, "change changeApprisal", _.debounce(this.render));
//                console.log('adding listener to ',a);
            }, this);
            // compile the template
            this.compiledTemplate = Handlebars.compile(this.template);
            this.compiledBodyTemplate = Handlebars.compile(this.bodyTemplate);
        },

        render: function() {
//            console.log('AlignmentTable rendering', this);
            // remove existing color pickers
            $("div.colorBall", this.$el).spectrum('destroy').remove();
            // re-render and insert html
            if(this.$('table').length === 0) {
                // render table elems and header
                this.$el.html(this.compiledTemplate({
                    molecules: this.attributes.molecules,
                    alignments: this.attributes.alignments
                }));

                // render color scheme picker
                var colorPickerPopover = $('<div/>', {class: "schemeKey"});
                _.forEach(_.keys(colorSchemes), function(schemeKey) {
                    var schemeOption = new ColorSchemeOption({
                        model: {
                            schemeKey:schemeKey,
                            colors: colorSchemes[schemeKey]
                        }}).render(this.$("th.colorSchemePicker"));
                    this.listenTo(schemeOption, 'selected', this.applyColorScheme);
                    colorPickerPopover.append(
                        schemeOption.$el
                    );
                }, this);
                colorPickerPopover.append($('<small class="text-muted clearfix"><em>Source: <a href="http://colorbrewer2.com/" target="_blank">Color Brewer</a><em></small>'))
                this.colorSchemePicker = this.$("th.colorSchemePicker").popover({
                    container: 'th.colorSchemePicker',
                    placement: 'right',
                    trigger: 'click ',
                    viewport: { selector: 'body', padding: 85 },
                    html: true,
                    title: 'Color Scheme',
                    content: colorPickerPopover
                });
            }

            // table body
            // todo: should be rendering each alignement individually
            this.$('tbody').html(this.compiledBodyTemplate({
                molecules: this.attributes.molecules,
                alignments: this.attributes.alignments
            }));

            // add new color pickers (once complete?)
            var that = this;
            $("div.colorBall", this.$el).spectrum({
                showInput: true,
                change: function(color) {
//                    console.log(color);
                    var data = $.data(this);
                    that.updateColor(data.alignmentindex, color.toHex());

                }
            });
            return this;
        },

        remove: function() {
            this.$('div.colorBall').spectrum('destroy').remove();
            this.$el.empty();
            this.undelegateEvents();
            this.stopListening();
            return this;
        },

        toggleVisibility: function(event) {
            var alignmentIndex = $(event.currentTarget).parent().data().alignmentindex;
//            console.log('toggleVisibility', this.attributes.alignments.at(alignmentIndex).get('hidden'));
            if(event.shiftKey && this.hasOwnProperty('lastVisibilityToggleIndex') &&
                this.lastVisibilityToggleIndex !== alignmentIndex) {
                // if holding down shift key and a previous alignment was hidden, implement shift-click
                // set all alignments between them to the value of the last clicked alignment
                var lastClickedVisibility = this.attributes.alignments.at(this.lastVisibilityToggleIndex).get('hidden');
                var incDec = this.lastVisibilityToggleIndex > alignmentIndex ? 1 : -1;
                for(var i = alignmentIndex; i != this.lastVisibilityToggleIndex; i += incDec) {
                    this.attributes.alignments.at(i).setAndApprise('hidden',lastClickedVisibility);
//                    this.setHighlight(i, lastClickedVisibility);
                }
            } else {
                // if not holding down shift key, simply toggle
                this.attributes.alignments.at(alignmentIndex).setAndApprise('hidden',
                    !this.attributes.alignments.at(alignmentIndex).get('hidden')
                );
            }
            this.lastVisibilityToggleIndex = alignmentIndex;
//            console.log(this.attributes.alignments.at(alignmentIndex));
        },

        toggleHighlight: function(event) {
            var alignmentIndex = $(event.currentTarget).parent().data().alignmentindex;
            if(this.attributes.alignments.at(alignmentIndex).get('visible')) {
                // shift-click
                if(event.shiftKey && this.hasOwnProperty('lastHighlightedIndex') &&
                    this.lastHighlightedIndex !== alignmentIndex) {
                    // if holding down shift key and a previous alignment was highlighted, implement shift-click
                    // set all alignments between them to the value of the last clicked alignment
                    var lastClickedHighlighted = this.attributes.alignments.at(this.lastHighlightedIndex).get('highlighted');
                    var incDec = this.lastHighlightedIndex > alignmentIndex ? 1 : -1;
                    for(var i = alignmentIndex; i != this.lastHighlightedIndex; i += incDec) {
                        this.setHighlight(i, lastClickedHighlighted);
                    }
                } else {
                    // if not holding down shift key, simply toggle
                    this.setHighlight(alignmentIndex,
                        !this.attributes.alignments.at(alignmentIndex).get('highlighted'));
                }
                this.lastHighlightedIndex = alignmentIndex;
                //            console.log(this.attributes.alignments.at(alignmentIndex));
            }
        },

        setHighlight: function(alignmentIndex, highlight) {
            if(this.attributes.alignments.at(alignmentIndex).get('visible')) {
                this.attributes.alignments.at(alignmentIndex).setAndApprise('highlighted', highlight);
                //            console.log(this.attributes.alignments.at(alignmentIndex));
            }
        },

        updateColor: function(index, color) {
            this.attributes.alignments.at(index).setAndApprise('color', chroma(color));
        },

        applyColorScheme: function(colorScheme) {
            // console.log('applyColorScheme');
            this.colorSchemePicker.popover('hide');
            if(this.attributes.alignments.length > colorScheme.colors.length) {
                // more alignments than colors, lets apply colors at an even scale
                var scale = chroma.scale(colorScheme.colors);
                this.attributes.alignments.forEach(function(alignment, index, alignments) {
                    alignment.setAndApprise('color', scale(index/alignments.length));
                });

            } else {
                // more colors than alignments, just set them in order
                this.attributes.alignments.forEach(function(alignment, index) {
                    alignment.setAndApprise('color', chroma(colorScheme.colors[index]));
                });
            }
        }



    });
});