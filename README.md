pocketfeaturedb
===============

PocketFEATURE Library

Teague Sterling, Tianyun Lui
2013-2014

Libraries Included
------------------

 * **FEATUREwarppers**: Wrappers for calling FEATURE binaries from Python
 * **PocketFEATURE**: Implementations of PocketFEATURE scripts and utilities in Python
 * **FEATUREdb**: FEATUREDB Implementation (currently empty)

 * **data**: Includes default background data for PocketFEATURE

Requirements
------------

 * Python 2.7
 * BioPython
 * Numpy
 * SciPy (For BioPython)
 * sh (For subprocess calling)
 * Munkres (for experimental alignment)

Installation
------------

 0. Install Python 2.7 (If needed)
 1. Install FEATUREwrappers (Dependencies will be installed)

        $ cd FEATUREwrappers
        $ python setup.py install
        $ cd ..

 2. Install PocketFEATURE (Dependencies will be installed)

        $ cd PocketFEATURE
        $ python setup.py install
        $ cd ..

Scripts
-------
### pf\_extract

   Find or list pockets around ligands and write as either a Pointfile or 
   list of Residues.

   **Examples:**

        # List ligands found in PDB
        $ pf_extract 1fo4.pdb -l
        # Generate pocket around "best" (biggest) ligand with specified PDB
        $ pf_extract somepdb.pdb -i 1fo4 -o somepdb.ptf
        # Generate pocket around ATP (Full Ligand ID and short)
        $ pf_extract 1qhx.pdb 1qhx/0/A/501/ATP
        $ pf_extract 1qhx.pdb ATP -o 1qhx-ATP.ptf

   **Command Usage:**

        usage: Identify and extract pockets around ligands in a PDB file
               [-h] [-i PDBID] [-o PTF] [--log LOG] [-d CUTOFF] [-p] [-r] [-l]
               [PDB] [LIG]
        
        positional arguments:
          PDB                   Path to PDB file [default: STDIN]
          LIG                   Ligand ID to build pocket around [default: <largest>]
        
        optional arguments:
          -h, --help            show this help message and exit
          -i PDBID, --pdbid PDBID
                                PDB ID to use for input structure [default: BEST
                                GUESS]
          -o PTF, --output PTF  Path to output file [default: STDOUT]
          --log LOG             Path to log errors [default: <open file '<stderr>',
                                mode 'w' at 0x7f05d94f4270>]
          -d CUTOFF, --distance CUTOFF
                                Residue active site distance threshold [default: 6.0]
          -p, --print-pointfile
                                Print point file (default behavior)
          -r, --print-residues  Print residue ID list instead of point file
          -l, --list-only       List residues instead of creating pocket

### pf\_featurize

   A wrapper around featurize that allows command line arguments to set
   or override environmental variables

   **Examples:**

        $ pf_featurize -P 1qhx-ATP.ptf \
                       --feature-dir=~/FEATURE/trunk \
                       --feature-bin=~/FEATURE/trunk \
                       --pdb-dir=~/db/pdb \
                       --dssp-dir=~/db/dssp > 1qhx-ATP.ff

   **Command Usage:**

        usage: Call featurize in a custom environment [-h] [-P [POINTILE]]
                                                      [-n [SHELLS]] [-w [WIDTH]]
                                                      [-x [HETATMS]]
                                                      [-l [PROPERTYFILE]]
                                                      [-s [SEARCH_DIR]]
                                                      [--feature-root [FEATURE_ROOT]]
                                                      [--feature-dir [FEATURE_DIR]]
                                                      [--feature-bin [FEATURE_BIN]]
                                                      [--pdb-dir [PDB_DIR]]
                                                      [--dssp-dir [DSSP_DIR]]
                                                      [PDB]
        
        positional arguments:
          PDB
        
        optional arguments:
          -h, --help            show this help message and exit
          -P [POINTILE]
          -n [SHELLS]
          -w [WIDTH]
          -x [HETATMS]
          -l [PROPERTYFILE]
          -s [SEARCH_DIR]
          --feature-root [FEATURE_ROOT]
          --feature-dir [FEATURE_DIR]
          --feature-bin [FEATURE_BIN]
          --pdb-dir [PDB_DIR]
          --dssp-dir [DSSP_DIR]


### pf\_compare
   Compute pairwise tanimoto similarities for two FEATURE files based
   on provided background files.

   **Examples:**

        $ pf_compare 1qhx-ATP.ff 1qrd-FAD.ff -b data/background.ff -n data/background.coeffs -o scores
        # Default background files are ./background.ff and ./background.coeffs
        $ pf_compare1qhx-ATP.ff 1qrd-FAD.ff > 1qhx-ATP-1qrd-FAD.scores

   **Command Usage:**

        usage: Compute tanimoto matrix for two FEATURE vectors with a background and score normalizations
               [-h] [-b FEATURESTATS] [-n COEFFICIENTS] [-o VALUES] [--log LOG]
               FEATUREFILE1 FEATUREFILE2
        
        positional arguments:
          FEATUREFILE1          Path to first FEATURE file
          FEATUREFILE2          Path to second FEATURE file
        
        optional arguments:
          -h, --help            show this help message and exit
          -b FEATURESTATS, --background FEATURESTATS
                                FEATURE file containing standard devations of
                                background [default: background.ff]
          -n COEFFICIENTS, --normalization COEFFICIENTS
                                Map of normalization coefficients for residue type
                                pairs [default: background.coeffs
          -o VALUES, --output VALUES
                                Path to output file [default: STDOUT]
          --log LOG             Path to log errors [default: STDERR]


### pf\_align
   Compute the best alignment of a scores file.

   **Examples:**

        # Using defaults (standard greedy alignment and cutoff of -0.15)
        $ pf_align 1qhx-ATP-1qrd-FAD.scores -o 1qhx-ATP-1qrd-FAD.aligned
        # Cutoff at 0.0
        $ cat 1qhx-ATP-1qrd-FAD.scores | pf_align -c 0 > 1qhx-ATP-1qrd-FAD.aligned

   **Command Usage:**

        usage: Align scores from a PocketFEATURE score matrix [-h] [-c CUTOFF]
                                                              [-s COLINDEX]
                                                              [-m ALIGN_METHOD]
                                                              [-o VALUES] [--log LOG]
                                                              SCOREFILE
        
        positional arguments:
          SCOREFILE             Path to score file [default: STDIN]
        
        optional arguments:
          -h, --help            show this help message and exit
          -c CUTOFF, --cutoff CUTOFF
                                Minium score (cutoff) to align [default: -0.15
          -s COLINDEX, --score-column COLINDEX
                                Value column index in score file to use for aligning
                                [default: 1]
          -m ALIGN_METHOD, --method ALIGN_METHOD
                                Alignment method to use (one of: munkres, greedy)
                                [default: greedy]
          -o VALUES, --output VALUES
                                Path to output file [default: STDOUT]
          --log LOG             Path to log errors [default: STDERR]

### pf\_vis

   Create a Pymol script to visualize the alignment.

   **Examples:**

        # Assuming default PDB file names, colors and radii
        $ pf_vis 1qhx-ATP.ptf 1qrd-FAD.ptf 1qhx-ATP-1qrd-FAD.aligned
        # Explictly specifying PDB names
        $ pf_vis 1qhx-ATP.ptf 1qrd-FAD.ptf 1qhx-ATP-1qrd-FAD.aligned \
                 --pdbA=somepdb.pdb --pdbB=../1qrd.pdb
        # Overriding colors
        $ pf_vis 1qhx-ATP.ptf 1qrd-FAD.ptf 1qhx-ATP-1qrd-FAD.aligned --colors=reds.colors

   **Command Usage:**

        usage: Create PyMol scripts to visualize an alignment [-h] [-A CMD1] [-B CMD2]
                                                              [--pdbA [PDB1]]
                                                              [--pdbB [PDB2]]
                                                              [--colors [COLORFILE]]
                                                              [--radii [RADIIFILE]]
                                                              [--log LOG]
                                                              POINTS1 POINTS2
                                                              ALIGNMENT
        
        positional arguments:
          POINTS1               Path to FEATURE point file
          POINTS2               Path to FEATURE point file
          ALIGNMENT             Path to PocketFEATURE alignment
        
        optional arguments:
          -h, --help            show this help message and exit
          -A CMD1, --outputA CMD1
                                Path to first command output file
          -B CMD2, --outputB CMD2
                                Path to second command output file
          --pdbA [PDB1]         Path to first PDB file
          --pdbB [PDB2]         Path to second PDB file
          --colors [COLORFILE]  File of 0.0-1.0 RGB colors to use
          --radii [RADIIFILE]   File of point radii to use
          --log LOG             Path to log errors [default: <open file '<stderr>',
                                mode 'w' at 0x7f4e15f61270>]

### run\_fp

   Run an entire PocketFEATURE calculation, writing out desired intermediate files

  **Examples:**

        # Only View alignment and scores (using all defaults)
        $ run_pf 1qrd.pdb 1qhx.pdb
        # Produce visualization Scripts and override backgrounds
        $ run_pf ../PDBA.pdb ../PDBB.pdb \
                 -b ../background.ff -n ../background.coeffs \
                 --pymolA=pdba.py --pymolb=pdbb.py
        # Save Pointfiles
        $ run_pf ../PDBA.pdb ../PDBB.pdb --ptfA=pdba.ptf --ptfB=pdbb.ptf

  **Command Usage:**

        usage: Identify and extract pockets around ligands in a PDB file
               [-h] [--ligandA [LIGA]] [--ligandB [LIGB]] [-b FEATURESTATS]
               [-n COEFFICIENTS] [-d CUTOFF] [-c CUTOFF] [-o ALIGNMENT]
               [--ptfA [PTFA]] [--ptfB [PTFB]] [--ffA [FFA]] [--ffB [FFB]]
               [--scores [SCORES]] [--pymolA [PYMOLA]] [--pymolB [PYMOLB]] [--log LOG]
               PDBA PDBB
        
        positional arguments:
          PDBA                  Path to first PDB file
          PDBB                  Path to second PDB file
        
        optional arguments:
          -h, --help            show this help message and exit
          --ligandA [LIGA]      Ligand ID to build first pocket around [default:
                                <largest>]
          --ligandB [LIGB]      Ligand ID to build second pocket around [default:
                                <largest>]
          -b FEATURESTATS, --background FEATURESTATS
                                FEATURE file containing standard devations of
                                background [default: background.ff]
          -n COEFFICIENTS, --normalization COEFFICIENTS
                                Map of normalization coefficients for residue type
                                pairs [default: background.coeffs
          -d CUTOFF, --distance CUTOFF
                                Residue active site distance threshold [default: 6.0]
          -c CUTOFF, --cutoff CUTOFF
                                Minium score (cutoff) to align [default: -0.15
          -o ALIGNMENT, --output ALIGNMENT
                                Path to alignment file [default: STDOUT]
          --ptfA [PTFA]         Path to first point file [default: None]
          --ptfB [PTFB]         Path to second point file [default: None]
          --ffA [FFA]           Path to first FEATURE file [default: None]
          --ffB [FFB]           Path to second FEATURE file [default: None]
          --scores [SCORES]     Path to scores file [default: None]
          --pymolA [PYMOLA]     Path to first PyMol script [default: None]
          --pymolB [PYMOLB]     Path to second PyMol script [default: None]
          --log LOG             Path to log errors [default: <open file '<stderr>',
                                mode 'w' at 0x7f5e988d9270>]
 
