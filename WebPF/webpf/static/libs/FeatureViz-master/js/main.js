// Filename: main.js
// config library urls
require.config({
    urlArgs: "bust=vb1.1",   // force cache-busting when there's a version update
//    urlArgs: "bust=" + (new Date()).getTime(),
    // todo: use bower and grunt to normalize/manage/version dependencies
    paths: {
        bootstrap: 'lib/bootstrap/js/bootstrap.min',
        promise: 'lib/promise-1.0.0',
        jquery: 'lib/jquery-1.11.1',
        jquery_ui: 'lib/jquery-ui-1.11.1/jquery-ui.min',
        jquery_touch: 'lib/jquery.ui.touch-punch.min',
        spectrum: 'lib/spectrum',
        underscore: 'lib/underscore',
        backbone: 'lib/backbone',
        localstorage: "lib/backbone.localStorage",
        chroma: 'lib/chroma.js-master/chroma.min',
        handlebars: 'lib/handlebars-v1.3.0',
        jmol: 'lib/jmol-14.0.13/jsmol/JSmol.min.nojq',
        jszip: 'lib/Stuk-jszip-64b3312/dist/jszip.min',
        jsziputils: 'lib/jszip-utils-master/dist/jszip-utils.min',
        numericjs: 'lib/numeric-1.2.6.min',
        kabsch: 'lib/kabsch',
        moleculeDisplayOptions: 'lib/displayOptions',
        filesaver: 'lib/FileSaver'
    },
    shim: {
        "jmol": {
            exports:"Jmol",
            deps: ['jquery'],
            init: function() {
                delete this.Jmol._tracker;
            }
        },
        "jquery_touch": {
            deps: ['jquery_ui']
        },
        "spectrum": {
            deps: ['jquery_ui', 'jquery_touch']
        },
        "moleculeDisplayOptions": {
            deps: ['jquery_ui']
        },
        "handlebars": {
            exports: "Handlebars"
        },
        "bootstrap": {
            deps: ['jquery_ui'],
            init: function() {
                $.fn.bootstrapBtn = $.fn.button.noConflict();
            }
        },
        "filesaver": {
            export: "saveAs"
        },
        "jsziputils": {
            deps: ['jszip'],
            exports: "JSZipUtils",
            init: function() {
                var ua = window.navigator.userAgent;
                var msie = ua.indexOf("MSIE ");
                if (msie > 0) {
                    // this content comes from jszip-utils-ie.js
                    var IEBinaryToArray_ByteStr_Script =
                        "<!-- IEBinaryToArray_ByteStr -->\r\n" +
                        "<script type='text/vbscript'>\r\n" +
                        "Function IEBinaryToArray_ByteStr(Binary)\r\n" +
                        "   IEBinaryToArray_ByteStr = CStr(Binary)\r\n" +
                        "End Function\r\n" +
                        "Function IEBinaryToArray_ByteStr_Last(Binary)\r\n" +
                        "   Dim lastIndex\r\n" +
                        "   lastIndex = LenB(Binary)\r\n" +
                        "   if lastIndex mod 2 Then\r\n" +
                        "       IEBinaryToArray_ByteStr_Last = Chr( AscB( MidB( Binary, lastIndex, 1 ) ) )\r\n" +
                        "   Else\r\n" +
                        "       IEBinaryToArray_ByteStr_Last = " + '""' + "\r\n" +
                        "   End If\r\n" +
                        "End Function\r\n" +
                        "</script>\r\n";

                    // inject VBScript
                    document.write(IEBinaryToArray_ByteStr_Script);

                    this.JSZipUtils._getBinaryFromXHR = function (xhr) {
                        var binary = xhr.responseBody;
                        var byteMapping = {};
                        for (var i = 0; i < 256; i++) {
                            for (var j = 0; j < 256; j++) {
                                byteMapping[ String.fromCharCode(i + (j << 8)) ] =
                                    String.fromCharCode(i) + String.fromCharCode(j);
                            }
                        }
                        var rawBytes = IEBinaryToArray_ByteStr(binary);
                        var lastChr = IEBinaryToArray_ByteStr_Last(binary);
                        return rawBytes.replace(/[\s\S]/g, function (match) {
                            return byteMapping[match];
                        }) + lastChr;
                    };

                }
            }
        }
    },
    onError: function() {
        console.log('ERR', arguments);
    }

});

require([
    // Load our app module and pass it to our definition function
    'views/openWorkbook', 'views/saveWorkbook', 'views/saveImages', 'views/appView'
], function(OpenWorkbookView, SaveWorkbookView, SaveImagesView, AppView){
    // todo: replace with Router?
    var QueryString = function () {
        // This function is anonymous, is executed immediately and
        // the return value is assigned to QueryString!
        var query_string = {};
        var query = window.location.search.substring(1);
        var vars = query.split("&");
        for (var i=0;i<vars.length;i++) {
            var pair = vars[i].split("=");
            // If first entry with this name
            if (typeof query_string[pair[0]] === "undefined") {
                query_string[pair[0]] = pair[1];
                // If second entry with this name
            } else if (typeof query_string[pair[0]] === "string") {
                query_string[pair[0]] = [ query_string[pair[0]], pair[1] ];
                // If third or later entry with this name
            } else {
                query_string[pair[0]].push(pair[1]);
            }
        }
        return query_string;
    } ();

    var FV = {};
    // FeatureViz event bus
    FV.vent = _.extend({}, Backbone.Events);

//            FV.loadAlignment(["1qrd", "1qhx"]);
    var alignmentMolecules = (QueryString.alignment && QueryString.alignment.indexOf('-') > 0) ?
        QueryString.alignment.split('-') : ['1qrd','1qrd2'];
    var alignmentLink = document.getElementById(alignmentMolecules.join('-') +'-link');
    if(alignmentLink) {
        alignmentLink.className = alignmentLink.className + ' active';
    }
    new OpenWorkbookView({
        el: document.getElementById('importModal'),
        model: FV
    }).render();

    var appView, imagesView, saveView;
    FV.vent.on('updateModels', function() {
        if(appView) {
            console.log('destroying old appview', FV);
            appView.remove();
        }
        console.log('creating new appview', FV);
        appView = new AppView({
            el: document.getElementById('featureVizContainer'),
            model: FV
        }).render();

        if(imagesView) {
            imagesView.remove();
        }
        imagesView = new SaveImagesView({
            el: document.getElementById('imageModal'),
            model: FV,
            button: $('#imageButton')
        }).render();

        if(!saveView) {
            saveView = new SaveWorkbookView({
                el: document.getElementById('saveModal'),
                model: FV,
                button: $('#exportButton')
            }).render();
        }
    });
//    App.initialize(alignmentMolecules);
//        FV.loadAlignment(alignmentMolecules);
});