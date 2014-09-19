PocketFEATURE
Tianyun Liu and Russ B Altman, Stanford University 2011


=================================================================================
0. Prepare data
PDB and dssp files (example, 1qhx.pdb and 1qhx.dssp).  
For some PDB, pre-process is necessary to remove duplicate atoms and hydrogen. 
=================================================================================
1. GenerateCavityPoint_Vectorize.pl
(1). There are different ways to define cavities (pockets) of a give protein.  
This script starts from a pre-defiend ligand and select residues withing 6 Angstroms.

1qhx.pdb=> 1qhx_ATP.pdb 
The ligand information is saved in a separate file (list1.txt). 
The four columns are: pdb_id, ligand_id, ligand_chain_id, ligand_index 

(2). The selected residues are centered at their functional atoms/centers. 
This step is called "point generation".

1qhx_ATP.pdb => 1qhx_ATP.ptf

(3). Then the script calls functions in FEATURE (featurize -P points > vectors) 
1qhx_ATP.ptf => 1qhx_ATP.ff 

(4) The output of GenerateCavityPoint_Vectorize.pl summarize the information of the cavity:
1qhx	ATP	A	501	31	21
1qrd	FAD	A	274	53	23
The last two columns are: 
number of non-hydrogen atoms and number of points in the cavity. 

=================================================================================
2. CompareTwoSites.pl 1qhx_ATP.ff 1qrd_FAD.ff All1160Cavity.std TcCutoff4Normalize.txt output.tmp

1. 1qhx_ATP.ff and  1qrd_FAD.ff are two pockets represented using FEATURE description. 
To compare two microenvironments (two FEATURE vectors), each vector is writen in a single *.ff.

2. 1qhx_ATP_1qhx_FAD.score has Tc and S(Tc) between every two microenvironments from two pockets. 
Note that only 72 types of allowed pairs (hard code in the script).

3. 1qhx_ATP_1qhx_FAD.align has the matched microenvironments between two pockets

4. output.tmp has the similarity score between two sites.  
If there is no matched microenvironments between two pockets, the output is 'NA'.

=================================================================================

Parameter files
All1160Cavity.std 
TcCutoff4Normalize.txt

