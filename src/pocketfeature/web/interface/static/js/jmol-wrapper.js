// ============================================================================
// DEPENDENCIES
// ============================================================================
// - jsmol/JSmol.min.nojq.js   JSmol library 
// - deployJava.js             Oracle Java support (http://java.com/js/deployJava.txt)
// - modernizr-canvas.min.js   Modernizr canvas support (http://modernizr.com)
// ----------------------------------------------------------------------------

// ============================================================================
// NOTES
// ============================================================================
// JSmol implements both a pure HTML5 Canvas/JavaScript molecular viewer and
// a Java Jmol-compatible molecular viewer.
//
// See JSmol documentation here: 
// http://sourceforge.net/projects/jsmol
//
// BUG IN JSmol
// XMLHttpRequest.responseType cannot be changed for synchronous HTTP(S) 
// requests made from the window context.
//
// This bug appears in Chrome. Ignore this bug.
// ----------------------------------------------------------------------------
function _WebFEATURE_ScanResults_UI_Jmol( jmolJarPath ) {
	var jmolOptions = {
		color:         "black",
		debug:         false,
		width:         590,
		height:        490,
		jarPath:       jmolJarPath,
		jarFile:       "JmolApplet.jar",
		j2sPath:       webfeature.url + "/jsmol/j2s",
		readyCallback: null,
	};
	var notes;
	if( Modernizr.canvas ) {
		jmolOptions.use = "HTML5";
		notes = 
			"<div id=\"view-notes\">Visualization powered by " +
			"<a href=\"http://sourceforge.net/projects/jsmol\">JSmol</a>, " +
			"which is written in JavaScript for HTML5. <br /> Viewer not showing " +
			"properly? <a href=\"javascript:location.reload()\">Reload</a></div>";

	} else if( deployJava.versionCheck( "1.4+" ) ) {
		notes = 
			"<div id=\"view-notes\">Visualization powered by " + 
			"<a href=\"http://jmol.sourceforge.net\">Jmol</a>, " +
			"which is based on Java. Viewer not showing properly? <br /> " +
			"<a href=\"javascript:location.reload()\">Reload</a>, " +
			"or <a href=\"http://jmol.sourceforge.net/#Learn+to+use+Jmol\">learn " +
			"more about Jmol set-up</a></div>";

	} else {
		notes = 
			"<div id=\"view-notes\">Visualization powered by " + 
			"<a href=\"http://jmol.sourceforge.net\">Jmol</a>, " +
			"which is based on Java. Viewer not showing properly? <br /> " +
			"Make sure Java is enabled for your browser, " +
			"<a href=\"javascript:location.reload()\">reload</a>, " +
			"or <a href=\"http://jmol.sourceforge.net/#Learn+to+use+Jmol\">learn " +
			"more about Jmol set-up</a></div>";
	}
	this.applet = Jmol.getApplet( "FEATURE_Hits_Viewer", jmolOptions );
	this.html( notes );
	
}

// ============================================================================
// AVOID POLLUTING THE NAMESPACE
// ============================================================================
if       ( typeof WebFEATURE === 'undefined' ) {
	WebFEATURE = { ScanResults : { UI : { Jmol : _WebFEATURE_ScanResults_UI_Jmol }}};

} else if( typeof WebFEATURE.ScanResults === 'undefined' ) {
	WebFEATURE.ScanResults = { UI : { Jmol : _WebFEATURE_ScanResults_UI_Jmol }};

} else if( typeof WebFEATURE.ScanResults.UI === 'undefined' ) {
	WebFEATURE.ScanResults.UI = { Jmol : _WebFEATURE_ScanResults_UI_Jmol };

} else {
	WebFEATURE.ScanResults.UI.Jmol = _WebFEATURE_ScanResults_UI_Jmol;
}


// ============================================================================
// CLASS PROTOTYPES
// ============================================================================

// ----------------------------------------------------------------------------
// script()
// ----------------------------------------------------------------------------
// Pass the given string for Jmol to evaluate
WebFEATURE.ScanResults.UI.Jmol.prototype.script = function( script ) {
	Jmol.script( this.applet, script );
}

// ----------------------------------------------------------------------------
// html()
// ----------------------------------------------------------------------------
// Have Jmol add the given HTML to the document
WebFEATURE.ScanResults.UI.Jmol.prototype.html = function( html ) {
	Jmol.jmolHtml( html );
}
