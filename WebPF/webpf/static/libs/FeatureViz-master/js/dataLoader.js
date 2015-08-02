/**
 * Created by nmew on 9/6/14.
 */
define([
    'jquery',
    'underscore',
    'backbone',
    'collections/poses',
    'collections/molecules',
    'collections/alignments',
    'models/alignment',
    'collections/points',
    'models/point',
    'models/featureViz',
    'chroma',
    'jszip',
    'jsziputils',
    'filesaver',
    'promise'
], function ($, _, Backbone, Poses, Molecules, Alignments, Alignment, Points, Point, FeatureViz, chroma, JSZip, JSZipUtils, saveAs) {

    var getAlignmentDirectories = function(molIds) {
        var query = molIds.reduce(function(previousVal, curVal, index){
            return previousVal +
                (index > 0 ? '&' : '') +
                'mol_id_' + (index+1) + '=' +
                curVal;
        }, '?');

        return Promise.resolve($.ajax({
            url: '../getAlignmentDirectories' + query,
            dataType: 'json'
        }));
    };
    var loadPointsToMolecule = function( molecule ) {
        var promise;
        if(typeof molecule.get('ptf') == "string") {
            promise = Promise.resolve($.ajax({
                url: molecule.get('ptf'),
                dataType: 'text',
                cache: false
            }));
        } else /*todo: assert if(molDef.ptf.size > 0) */{
            promise = Promise.resolve().then( function(){
                return molecule.get('ptf').asText();
            });
        }
        return promise.then(function( csvAsString ) {
            var points = new Points;
            var rows = csvAsString.split('\n');
            for (var row = 0; row < rows.length; row++) {
                try {
                    points.push(new Point({
                        molecule: molecule,
                        rowStr: rows[row],
                        delim: "\t"
                    }, {parse: true, sort: false}));
                } catch (e) {
                    console.warn("Error while parsing ptf file.", e);
                }
            }

            molecule.set('points', points);
            molecule.set('ptfText', csvAsString);
            return molecule;
        });
    };


    var getColorScale = function(count) {
        // todo: get color scale from featureSettings/workbookSettings
        var brewerScale = 'Set1';
        if(count > 9) {
            brewerScale = 'Set3';
        }
        return {scale: chroma.scale(brewerScale), count: chroma.brewer[brewerScale].length};
    };


    var loadAlignments = function(molecules, colorScale) {
        var promise;
        if(typeof molecules.first().get('align') == 'string') {
            Promise.resolve($.ajax({
                /* todo: set a root url somewhere and use it here */
                url: molecules.first().get('align'),
                dataType: 'text',
                cache: false
            }));
        } else {
            console.log(molecules.first().get('align'));
            promise = Promise.resolve().then(function(){
                return molecules.first().get('align').asText();
            });
        }
        return promise.then(function (csvAsString) {
            "use strict";
            var alignments = new Alignments;
            var rows = csvAsString.trim().split('\n');
			var re = /;?\t/;
            rows = _.map(rows, function(row){ return row.split( re ); });
            // set color scale based on scores
            var colorPallet = getColorScale( rows.length );
            var divisor = (colorPallet.count > rows.length ? colorPallet.count : rows.length) - 1;
            colorScale = colorPallet.scale;
            for (var row = 0; row < rows.length; row++) {
                var cols = rows[row];
                if(cols.length === 3) {
                    //todo: update for > 2 molecules
                    alignments.push(new Alignment({
                        pointDescriptions: [cols[0],cols[1]],
                        points: [molecules.at(0).get('points').get(cols[0]), molecules.at(1).get('points').get(cols[1])],
                        score: +cols[2],
                        color: colorScale(row/divisor)
                    }));
                }
            }
            // function in .then is called with alignments
            return alignments;
        });
    };

    var loadData = function(molIds) {
        var FV = {};

        var loadMoleculesPromise;

        if(typeof molIds[0] == 'string') {
            loadMoleculesPromise = getAlignmentDirectories(molIds).then(function (molDirsResults) {
                // add to global FV
                if(molDirsResults.success.toLowerCase() === 'true') {
                    FV.molDefs = molDirsResults.mols;
                    return FV.molDefs;
                } else {
                    console.error("error loading moldefs", molDirsResults.message, arguments);
                    throw new Error("error loading moldefs: " + molDirsResults.message);
                }
            })['catch'](function(){
                console.error("error loading moldefs", arguments);
                throw new Error("error loading moldefs");
            });
        } else {
            loadMoleculesPromise = Promise.resolve().then(function(){
                FV.molDefs = molIds;
                return FV.molDefs;
            });
        }

        // load alignment directories then load the point definitions in each
        return loadMoleculesPromise.then(function (molDirsResults) {
            FV.molecules = new Molecules(molDirsResults);
            return FV;
        })['catch'](function(){
            console.error("error loading molecules", arguments);
            throw new Error("error loading molecules");
        }).then(function () {

            // asynchronously load all ptf files, create points and add to molecules
            return Promise.all( FV.molecules.map(loadPointsToMolecule) );

        })['catch'](function(){
            console.error("error loading points", arguments);
            throw new Error("error loading points");
        }).then(function () {

            // get alignment file and update models
            FV.colorScale = {};
            return loadAlignments(FV.molecules, FV.colorScale);

        })['catch'](function(){
            console.error("error loading alignments", arguments);
            throw new Error("error loading alignments");
        }).then(function (alignments) {
            FV.alignments = alignments;
            if( !FV.featureVizSettings ) {
                FV.featureVizSettings = new FeatureViz({});
            }
            // set initial score cutoff based on alignment scores
            FV.featureVizSettings.set('alignmentScoreCutoff', FV.alignments.last().get('score') + 0.001);
            // sort points in collections by alignment score
            FV.molecules.forEach(function (mol) {
                mol.get('points').sort();
            });
            return FV;
        })['catch'](function(){
            console.error("error loading views", arguments);
            throw new Error("error loading views");
        });
    };

    var safeToUnzip = function(fileMetaData) {
        return (fileMetaData.type == "application/zip" || fileMetaData.type == "application/x-zip") && fileMetaData.size < 2000000;
    };

    var getWorkbookSettingsFromZip = function(zip) {
        var file = _.findWhere(zip.files, {name: 'workbook.json'});
        var settings = {};
        if(file) {
            settings = JSON.parse(file.asText());
        }
        return settings;
    };

    var getMoleculeDefinitionsFromZip = function(zip) {
        var requiredFileTypesForEachModel = ['pdb','ptf'];
        var moleculeDefinitions = [];
        var alignmentFile = _.find(zip.files, function(file){ return file.name.indexOf('.align') >= (file.name.length-'.align'.length)});
        var splitCols = alignmentFile.asText().split('\n')[0].split('\t');
        var molIds = [];
        for(var i=0; i < splitCols.length-1; i++) {
            var molid = splitCols[i].split('_')[0];
            molIds.push(molid);
            moleculeDefinitions.push({id:molid});
        }
        var fileName = molIds.join('-');
        var fileNames = _.pluck(zip.files, 'name');
        // should have at least (molCount * fileTypesPerModel) + 1 files
        if (fileNames.length < (requiredFileTypesForEachModel.length * molIds.length) + 1) {
            return false;
        }
        // all required files should exist and be named properly
        _.forEach(requiredFileTypesForEachModel, function(ext){
            _.forEach(moleculeDefinitions, function(molDef) {
                var fullFileName = molDef.id + '.' + ext;
                var file = _.findWhere(zip.files, {name: fullFileName});
                if (file) {
                    molDef[ext] = file;
                    molDef[ext + "Text"] = file.asText();
                } else {
                    console.error("could not find " + fullFileName);
                    return false;
                }
            });
        });
        // align file
        var alignFile = _.find(zip.files, function(file){return file.name && file.name.indexOf('.align') > -1;});
        if(alignFile) {
            _.forEach(moleculeDefinitions, function(molDef){
                molDef.align = alignFile;
                molDef.alignText = alignFile.asText();
            });
        } else {
            console.error("could not find " + fileName + '.align');
            return false;
        }
        return moleculeDefinitions;
    };

    var getZip = function(binaryFile) {
        return new JSZip(binaryFile);
    };

    var loadByPdbIds = function(pdbIds) {};

    /**
     * Takes target result from FileReader.readAsArrayBuffer and returns promise which
     * loads molecules and Alignments
     * @param zipFileBinary target result from FileReader.readAsArrayBuffer
     * @returns Promise with molecules, arrays and settings
     */
    var loadByZipFile = function(zipFileBinary) {
        var zip = getZip(zipFileBinary);

        return Promise.resolve().then(function() {
            // read the content of the file with JSZip
            console.log("unzipped. ", zip);
            // get the required filenames and file data as text
            var moleculeDefs = getMoleculeDefinitionsFromZip( zip );
            console.log( moleculeDefs );

            return moleculeDefs;
        })
        .then( loadData )
        .then(function(FV) {
            // workbookSettings has:
            //  alignments: Array[4]
            //  currentPose: Array[2]
            //  renderingOptions: {}
            var workbookSettings =  getWorkbookSettingsFromZip(zip);
            if(!_.isEmpty(workbookSettings)) {
                // set any rendering options saved in workbook to current featureVizSettings
                FV.featureVizSettings.set(workbookSettings.renderingOptions);
                // should already be sorted, but just in case
                var sortedWorkbookAlignments = _.sortBy(workbookSettings.alignments, 'score');
                // set any alignment attributes saved in workbook to current alignment settings
                FV.alignments.forEach(function(alignment, index){
                    // make sure we're dealing w/ the same alignment
                    if(_.difference(alignment.get('pointDescriptions'),
                        sortedWorkbookAlignments[index].pointDescriptions).length === 0) {
                        alignment.set('color', chroma(sortedWorkbookAlignments[index].hexColor));
                        alignment.set('cutoff', sortedWorkbookAlignments[index].cutoff);
                        alignment.set('hidden', sortedWorkbookAlignments[index].hidden);
                        alignment.set('highlighted', sortedWorkbookAlignments[index].highlighted);
                    } else {
                        throw new Error("Workbook settings do not match alignments.");
                    }
                });
            }
            FV.poses = workbookSettings.poses ? new Poses(workbookSettings.poses) : new Poses();
            return FV;
        });
    };


    var saveToDisk = function(FV, workbookName) {
        /* workbook/settings */
        var workbook = {};
        workbook.currentPose = FV.currentPose || " ";               // current pose
        workbook.poses = FV.poses.toJSON();                           // pose scripts
        workbook.alignments = FV.alignments.map(function(alignment) {
            return alignment.pick(['score', 'hexColor', 'pointDescriptions', 'cutoff', 'hidden', 'highlighted']);
        });               // alignments
        workbook.renderingOptions = FV.featureVizSettings.toJSON(); // all tool options


        var zip = new JSZip();
        try {
            zip.file("workbook.json", JSON.stringify(workbook), {date: new Date()}); // workbook.json
            var alignName;
            if(typeof FV.molecules.first().get('align') == "object") {
                var alignFile = FV.molecules.first().get('align');
                alignName = alignFile.name;
                zip.file(alignFile.name, alignFile.asText(), alignFile.options);     // mol1-mol2.align
                FV.molecules.forEach(function(mol){
                    zip.file(mol.get('pdb').name, mol.get('pdb').asText(), mol.get('pdb').options);   // mol1.pdb
                    zip.file(mol.get('ptf').name, mol.get('ptf').asText(), mol.get('ptf').options);   // mol1.ptf
                });
            } else {
                var alignURL = FV.molecules.first().get('align');
                alignName = alignURL.slice(alignURL.lastIndexOf("/") + 1);
                zip.file(alignName, FV.molecules.first().get('alignText'));   // mol1-mol2.align
                FV.molecules.forEach(function(mol){
                    var pdbName = mol.get('pdb').slice(mol.get('pdb').lastIndexOf("/") + 1);
                    var ptfName = mol.get('ptf').slice(mol.get('ptf').lastIndexOf("/") + 1);
                    zip.file(pdbName, mol.get('pdbText'));             // mol1.pdb
                    zip.file(ptfName, mol.get('ptfText'));             // mol1.ptf
                });
            }

            var blob = zip.generate({type:"blob"});
            saveAs(blob, workbookName + "-" + alignName.replace(".align", ".zip"));
        } catch(e) {
            console.error(e);
            return false;
        }
    };

    /**
     * Takes a url to a zip file and returns promise which loads molecules and Alignments
     * @param zipFileURL string url pointing to zip file
     * @returns Promise with molecules, arrays and settings
     */
    var loadByZipFileURL = function(zipFileURL) {
        return new Promise(function(resolve, reject) {
            JSZipUtils.getBinaryContent(zipFileURL, function(err, data) {
                if(err) {
                    reject(err); // or handle err
                } else {
                    resolve(loadByZipFile(data));
                }
            });
        });
    };

    return {
        saveToDisk: saveToDisk,
        loadData: loadData,
        safeToUnzip: safeToUnzip,
        loadByZipFile: loadByZipFile,
        loadByZipFileURL: loadByZipFileURL
    };
});
