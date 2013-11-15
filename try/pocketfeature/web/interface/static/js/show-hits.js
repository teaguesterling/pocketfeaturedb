// ============================================================================
// DEPENDENCIES
// ============================================================================
// - jmol-wrapper.js           WebFEATURE Jmol Wrapper
// - jquery.js                 jQuery
// ----------------------------------------------------------------------------

// ============================================================================
// CLASS DEFINITIONS
// ============================================================================
function _WebFEATURE_ScanResults_Hits( atoms ) {
	this.atoms      = atoms
	this.PRECISION  = 0.1; // Hits agree if they are within 0.1 Angstroms
	this.size       = 400;
	this.hits       = {};
	this.cutoff     = {};
	this.enabled    = {};
	this.colors     = {
		'NB':     'red', 
		'SVM':    'blue',
		'NB-SVM': 'green'
	};
	this.showAgreed = false;
	this.findAgreements();
}

// ============================================================================
// AVOID POLLUTING THE NAMESPACE
// ============================================================================
if       ( typeof WebFEATURE === 'undefined' ) {
	WebFEATURE = { ScanResults : { Hits : _WebFEATURE_ScanResults_Hits } };

} else if( typeof WebFEATURE.ScanResults === 'undefined' ) {
	WebFEATURE.ScanResults = { Hits : _WebFEATURE_ScanResults_Hits };

} else {
	WebFEATURE.ScanResults.Hits = _WebFEATURE_ScanResults_Hits;
}

// ============================================================================
// CLASS PROTOTYPES
// ============================================================================

// ----------------------------------------------------------------------------
// enable( mlMethod ) and disable( mlMethod )
// ----------------------------------------------------------------------------
// Sets the viewer state for the given machine learning method
WebFEATURE.ScanResults.Hits.prototype.enable  = function ( machineLearningMethod ) { this.enabled[ machineLearningMethod ] = true; }
WebFEATURE.ScanResults.Hits.prototype.disable = function ( machineLearningMethod ) { this.enabled[ machineLearningMethod ] = false; }

// ----------------------------------------------------------------------------
// useJmol( jmol )
// ----------------------------------------------------------------------------
// Associates the viewer to use with this model
WebFEATURE.ScanResults.Hits.prototype.useJmol = function( jmol ) {
	this.jmol = jmol;
}

// ----------------------------------------------------------------------------
// findAgreements()
// ----------------------------------------------------------------------------
// Finds ML prediction agreements
WebFEATURE.ScanResults.Hits.prototype.findAgreements = function() {
	for( var i = 0; i < this.atoms.length; i++ ) {
		var atom = this.atoms[ i ];
		var x    = Math.round( atom.x / this.PRECISION );
		var y    = Math.round( atom.y / this.PRECISION );
		var z    = Math.round( atom.z / this.PRECISION );
		var xyz  = x + "," + y + "," + z;
		if( typeof this.hits[ xyz ] === 'undefined' ) {
			this.hits[ xyz ] = [ atom ];
		} else {
			this.hits[ xyz ].push( atom );
		}
	}
};

// ----------------------------------------------------------------------------
// setCutoff( mlMethod, cutoff )
// ----------------------------------------------------------------------------
// Set the cutoff for ML prediction scores for visualization; scores below this
// cutoff are not visualized.
WebFEATURE.ScanResults.Hits.prototype.setCutoff = function( machineLearningMethod, cutoff ) {
	this.cutoff[ machineLearningMethod ] = cutoff;
};


// ----------------------------------------------------------------------------
// showAgreedHits( bool )
// ----------------------------------------------------------------------------
// Cause the viewer to visualize the hits
WebFEATURE.ScanResults.Hits.prototype.showAgreedHits = function( bool ) {
	this.showAgreed = bool;
}

// ----------------------------------------------------------------------------
// updateView()
// ----------------------------------------------------------------------------
// Cause the viewer to visualize the hits
WebFEATURE.ScanResults.Hits.prototype.updateView = function() {
	if( typeof this.jmol === 'undefined' ) return;

	this.jmol.script( "select [HIT]; spacefill 0;" );
	for( var xyz in this.hits ) {
		// ===== FILTER LOW SCORING HITS
		var relevant   = [];
		for( var i = 0; i < this.hits[ xyz ].length; i++ ) {
			var hit = this.hits[ xyz ][ i ];
			if( hit.score >= this.cutoff[ hit.name ]) {
				relevant.push( hit );
			}
		}
		if( relevant.length == 0 ) continue;

		// ===== SHOW HIGH SCORING HITS
		var agreements         = relevant.length - 1;
		var hit                = relevant[ 0 ];
		var color              = '';

		// ===== AGREEMENTS USE SPECIAL COLORS
		// If there are agreements, then the agreements are uniquely named by
		// joining all ML names in alphabetical order, with hyphens in between.
		if( agreements > 0 ) {
			relevant = relevant.sort( function( a, b ) { if( a.name < b.name ) { return -1; } else if( a.name > b.name ) { return 1; } else { return 0; } } );
			var methods = [];
			for( i = 0; i < relevant.length; i++ ) {
				if( ! this.enabled[ relevant[ i ].name ] ) { continue; }
				methods.push( relevant[ i ].name );
			}
			var mlMethods = methods.join( '-' ); // e.g. NB-SVM
			color         = this.colors[ mlMethods ];

		// ===== HITS PREDICTED BY A SINGLE METHOD USE THEIR DESIGNATED COLORS
		} else {
			if( this.showAgreed )            continue; // Skip if user only wants to see agreed hits
			if( ! this.enabled[ hit.name ] ) continue; // Skip if user doesn't want to see this method
			color         = this.colors[ hit.name ];
		}
		var size      = this.size;
		var renderHit = "select atomno=" + hit.num + "; color " + color + "; spacefill " + size + ";"
		this.jmol.script( renderHit );
	}
};
