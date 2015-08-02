/**
 * Created by nmew on 8/22/14.
 */
define([
    'jquery',
    'underscore',
    'backbone',
    'jquery_ui'
], function ($, _, Backbone) {
    return Backbone.View.extend({
        defaultAttributes: {
            max: 100,
            min: 0,
            step: 1,
            tooltipPlacement: 'bottom',
            tooltipValue: 'model',
            slideModelParam: [],
            modelParam: []
        },
        initialize: function (options) {
            // use specified value modifiers
            _.extend(this, _.pick(options, "modelValueToUiValue", "uiValueToModelValue"));
            // bind methods to this instance
            _.bindAll(this, 'onSliderSlide', 'onSliderChange', 'getTooltipText', 'setSliderUi', 'setOptions');
            // fill in attributes with default values
            _.defaults(this.attributes, this.defaultAttributes);
            // make sure modelParams and slideModelParams are defined as arrays
            this.attributes.modelParam = _.isArray(this.attributes.modelParam)
                ? this.attributes.modelParam
                : [this.attributes.modelParam];
            this.attributes.slideModelParam = _.isArray(this.attributes.slideModelParam)
                ? this.attributes.slideModelParam
                : [this.attributes.slideModelParam];
        },
        render: function () {
            // render slider
            var slider = this.$el.slider({
                max: this.attributes.max,
                min: this.attributes.min,
                step: this.attributes.step,
                values: _.map(this.attributes.modelParam, function (param) {
                    return this.modelValueToUiValue(this.model.get(param));
                }, this),
                slide: this.onSliderSlide,
                change: this.onSliderChange
            });

            // render handle text
            var handles = slider.find(".ui-slider-handle");
            if(this.attributes.handlerText) {
                for (var i = 0; i < this.attributes.handlerText.length; i++) {
                    $(handles[i]).append(
                        "<span class='handlerText'>" + this.attributes.handlerText[i] + "</span>"
                    );
                }
            }

            // render tooltip
            var tooltipOptions = {
                position: 'absolute',
                textAlign: 'center',
                left: '-1.5em',
                width: '4em'
            };
            switch (this.attributes.tooltipPlacement) {
                case 'bottom':
                    tooltipOptions.top = 15;
                    break;
                case 'top':
                    tooltipOptions.bottom = 15;
            }
            this.tooltips = _.map(this.attributes.modelParam, function (param, index) {
                var handleTooltip = this.attributes.handlerNames
                    ? 'title="' + this.attributes.handlerNames[index] + '" '
                    : '';
                return $('<div class="slider-tooltip" ' + handleTooltip +
                    'data-placement="' + this.attributes.tooltipPlacement + '"' +
                    'container="body"/>')
                    .css(tooltipOptions)
                    .text(this.attributes.tooltipValue === 'model'
                        ? this.model.get(param)
                        : this.modelValueToUiValue(this.model.get(param)));
            }, this);

            // add value tooltips to each handle
            for (var i = 0; i < this.tooltips.length; i++) {
                $(handles[i]).append(this.tooltips[i]);
            }
            this.$('[title]').tooltip();
            return this;
        },
        remove: function() {
            _.each(this.tooltips, function($tooltip){
                $tooltip.remove();
            });
            this.$el.slider('destroy');
            this.undelegateEvents();
            this.stopListening();
        },
        setOptions: function() {
            return this.$el.slider.apply(this.$el.slider(), arguments);
        },
        setSliderUi: function(ui) {
            if (!_.isEmpty(this.attributes.slideModelParam)) {
                for (var i = 0; i < this.attributes.slideModelParam.length; i++) {
                    this.model.set(this.attributes.slideModelParam[i], this.uiValueToModelValue(ui.values[i]));
                }
            }
        },
        onSliderSlide: function (event, ui) {
            // set sliderModelParams
            // set tooltips
            for (var i = 0; i < this.tooltips.length; i++) {
                this.tooltips[i].text(this.getTooltipText(ui.values[i]));
            }
//            console.log('sliding '+this.attributes.slideModelParam);
            _.defer(this.setSliderUi, ui);

        },
        onSliderChange: function (event, ui) {
            this.trigger('sliderChange:'+this.attributes.modelParam);
            this.trigger('sliderChange');
            // set modelParams
            for (var i = 0; i < this.attributes.modelParam.length; i++) {
                this.model.set(this.attributes.modelParam[i], this.uiValueToModelValue(ui.values[i]));
            }
            // set sliderModelParams
            if (!_.isEmpty(this.attributes.slideModelParam)) {
                for (i = 0; i < this.attributes.slideModelParam.length; i++) {
                    this.model.set(this.attributes.slideModelParam[i], this.uiValueToModelValue(ui.values[i]));
                }
            }
            // set tooltips
            for (i = 0; i < this.tooltips.length; i++) {
                this.tooltips[i].text(this.getTooltipText(ui.values[i]));
            }
        },
        getTooltipText: function (uiValue) {
            return this.attributes.tooltipValue === 'model'
                ? this.uiValueToModelValue(uiValue)
                : uiValue;
        },
        modelValueToUiValue: function (value) {
            return value;
        },
        uiValueToModelValue: function (value) {
            return value;
        }
    });

});