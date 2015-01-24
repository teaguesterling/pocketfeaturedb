#! /usr/bin/perl
# Tianyun Liu 2011
# Stanford University
#=================================================================================================#
use File::Copy;
use List::MoreUtils qw(uniq);
#=================================================================================================#
if ($#ARGV != 1)
        {print "usage: GenerateCavity.pl list(pdbid-ligandtype-ligandchain-ligandid)  cutoff(6A)\n";exit; }
my $input=$ARGV[0];
my $cutoff=$ARGV[1];
#=================================================================================================#
open(IN, $input)|| die "cannot open";my @line=<IN>;close (IN);
foreach $line(@line)
   	{
	chomp $line;
	my @tmp1=split(/\t/, $line);
#	$tmp1[0]=~tr/A-Z/a-z/;
	$oriFile=$tmp1[0].".pdb";
	$ligFile=$tmp1[0]."_".$tmp1[1].".lig";
	$numberLigandAtoms=get_ligand_file($ligFile,$oriFile, $tmp1[1], $tmp1[2],$tmp1[3]);

	$pdbFile=$tmp1[0].".pdb";
	$ptfFile=$tmp1[0]."_".$tmp1[1].".ptf";
	$ffFile=$tmp1[0]."_".$tmp1[1].".ff";
	$cavityFile=$tmp1[0]."_".$tmp1[1].".pdb";
	$tag=$tmp1[0]."_".$tmp1[2]."_".$tmp1[3]."_".$tmp1[1];
	$residues_number=generate_points_near_ligands($pdbFile, $ligFile, $cavityFile, $ptfFile, $tag);
	generate_vectors($ptfFile, $ffFile);

	print $line."\t".$numberLigandAtoms."\t".$residues_number."\n";
	}
#------------------------------------------------------------------------------------------#
sub get_ligand_file
{
my ($ligFile, $oriFile, $ligType, $ligChain, $ligIndex)=@_;

open (MYL, ">$ligFile") || die "cannot open $ligFile\n";close MYL;
open (MYL, ">>$ligFile") || die "cannot open $ligFile\n";
my @AllHETA=`grep 'HETATM' $oriFile`;
my $atomNumber=0;
foreach $ALLHETA(@AllHETA)
	{
	chomp $ALLHETA;
	if (($ligType eq substr($ALLHETA, 17,3)) && ($ligIndex == trimLine(substr($ALLHETA, 22,4))))
		{
		my $chain=substr($ALLHETA, 21,1);
		if ($chain eq $ligChain) {print MYL $ALLHETA."\n"; $atomNumber ++;}
		elsif (($chain eq " ") && ($ligChain eq "-"))
                	{print MYL $ALLHETA."\n"; $atomNumber ++;}
		}
        }
close MYL;
return $atomNumber;
}
#------------------------------------------------------------------------------------------#
sub generate_points_near_ligands
{
my ($pdbFile, $ligFile, $cavityFile, $ptfFile, $tag)=@_;
my $PDBID=substr($pdbFile, -8, 4);
open(PTF, ">$ptfFile")|| die "cannot open"; close (PTF);open(PTF, ">>$ptfFile")|| die "cannot open";
open(CAV, ">$cavityFile")|| die "cannot open"; close (CAV);open(CAV, ">>$cavityFile")|| die "cannot open";

#read in ligand files:
my @ligandAtoms=`grep ^HETATM $ligFile`;

#read pdb files
my @CoorLines=`grep ^ATOM $pdbFile`;
my @allIndex=qw();
#get sequence
foreach $CoorLines(@CoorLines)
	{
	chomp $CoorLines;
	# residue index: residueNumber_residueName_chainID
	my $residue_index_all=trimLine(substr($CoorLines, 22, 4))."_".threeLetterRes2oneLetter(substr($CoorLines, 17, 3))."_".substr($CoorLines, 21, 1);
	push (@allIndex, $residue_index_all);
	}
my @index=uniq(@allIndex);

my $total=0;
my @selectedResidueList=qw();
foreach $index(@index)
	{
	my @atomLines=get_coordinate_lines_of_a_residue(\@CoorLines,$index);
	my @centers=calculate_center(\@atomLines, $index);
	#return value frm <calculate_center>: residueNumber_residueName_chainID."\t".coordinates connected by "\t".
	my $poiNumber=0;
	foreach $centers(@centers)
		{
		my $dis=find_shortest_dis_between_atom_ligands(\@ligandAtoms, $centers);
                #ADDED!!!
                print $dis."\t".$tmpIndex;;
		if ($dis<=$cutoff)
			{
			$poiNumber++;
			$total++;
			my @tmpCoor=split(/\t/, $centers);
			my @tmpIndex=split("_", $tmpCoor[0]);
			push (@selectedResidueList,$tmpCoor[0]);
			print PTF $PDBID."\t". $tmpCoor[1]."\t".$tmpCoor[2]."\t".$tmpCoor[3]."\t#\t".$tag."_".$tmpIndex[0]."_".$tmpIndex[1]."_".$poiNumber."_".$tmpIndex[2]."\n";
			}
		}
   	}

my @cavityResidue=uniq(@selectedResidueList);
foreach $cavityResidue(@cavityResidue)
	{
	my @lineResidue=get_coordinate_lines_of_a_residue(\@CoorLines, $cavityResidue);
	foreach $lineResidue(@lineResidue)
		{print CAV $lineResidue."\n";}
	}

close PTF; close CAV;
return $total;
}
#------------------------------------------------------------------------------------------#
sub get_coordinate_lines_of_a_residue
{
my ($refLine, $index)=@_;
my @lines=@$refLine;
my @tmp2=split("_", $index);
my @atoms=qw();
foreach $lines(@lines)
     {
	 if ((substr($lines, 21, 1) eq $tmp2[2])
       &&(threeLetterRes2oneLetter(substr($lines, 17, 3)) eq $tmp2[1])
       && (trimLine(substr($lines, 22, 4)) == $tmp2[0]))
             { push (@atoms, $lines)};
     }
return @atoms;
}
#------------------------------------------------------------------------------------------#
sub find_shortest_dis_between_atom_ligands
{
my ($refLigand, $centers) =@_;
my @ligand=@$refLigand;
chomp $centers;
my @tmp3=split(/\t/, $centers);
my @disBetweenPointsLigands=qw();
foreach $ligand(@ligand)
        {
        my $X=trimLine(substr($ligand, 30, 8));
        my $Y=trimLine(substr($ligand, 38, 8));
        my $Z=trimLine(substr($ligand, 46, 8));
        my $dis=sqrt(($X-$tmp3[1])*($X-$tmp3[1]) + ($Y-$tmp3[2])*($Y-$tmp3[2])+ ($Z-$tmp3[3])*($Z-$tmp3[3]));
		push (@disBetweenPointsLigands, $dis);
        }
my @sorted=sort{$a<=>$b}@disBetweenPointsLigands;
# ADDED!!!!
print $sorted;
return($sorted[0]);
}
#----------------------------------------------------------------------------------------#
sub calculate_center
{
my ($refArr, $index)=@_;
my @tmp4=split("_", $index); my $type=$tmp4[1];
my @centers=qw();
if ($type eq "G")
	{$cen=get_coor_of_an_atom($refArr,"CA"); if ($cen !=0){$cen=$index."\t".$cen; push(@centers, $cen);}}
elsif ($type eq "C")
	{$cen=get_coor_of_an_atom($refArr,"SG");if ($cen !=0){$cen=$index."\t".$cen;push(@centers, $cen);}}
elsif ($type eq "R")
	{$cen=get_coor_of_an_atom($refArr,"CZ");if ($cen !=0){$cen=$index."\t".$cen;push(@centers, $cen);}}
elsif ($type eq "S")
	{$cen=get_coor_of_an_atom($refArr,"OG");if ($cen !=0){$cen=$index."\t".$cen;push(@centers, $cen);}}
elsif ($type eq "T")
	{$cen=get_coor_of_an_atom($refArr,"OG1");if ($cen !=0){$cen=$index."\t".$cen;push(@centers, $cen);}}
elsif ($type eq "K")
	{$cen=get_coor_of_an_atom($refArr,"NZ");if ($cen !=0){$cen=$index."\t".$cen;push(@centers, $cen);}}
elsif ($type eq "M")
	{$cen=get_coor_of_an_atom($refArr,"SD");if ($cen !=0){$cen=$index."\t".$cen;push(@centers, $cen);}}
elsif (($type eq "A") ||($type eq "L")||($type eq "I")||($type eq "V"))
	{$cen=get_coor_of_an_atom($refArr,"CB");if ($cen !=0){$cen=$index."\t".$cen;push(@centers, $cen);}}

elsif ($type eq "D")
	{$cen=get_average($refArr,"OD1 CG OD2");if ($cen !=0){$cen=$index."\t".$cen;push(@centers, $cen);}}
elsif ($type eq "E")
	{$cen=get_average($refArr,"OE1 CD OE2");if ($cen !=0){$cen=$index."\t".$cen;push(@centers, $cen);}}
elsif ($type eq "H")
	{$cen=get_average($refArr,"NE2 ND1");if ($cen !=0){$cen=$index."\t".$cen;push(@centers, $cen);}}
elsif ($type eq "N")
	{$cen=get_average($refArr,"OD1 CG ND2");if ($cen !=0){$cen=$index."\t".$cen;push(@centers, $cen);}}
elsif ($type eq "P")
	{$cen=get_average($refArr,"N CA CB CD CG");if ($cen !=0){$cen=$index."\t".$cen;push(@centers, $cen);}}
elsif ($type eq "Q")
	{$cen=get_average($refArr,"OE1 CD NE2");if ($cen !=0){$cen=$index."\t".$cen;push(@centers, $cen);}}
elsif ($type eq "F")
	{$cen=get_average($refArr,"CG CD1 CD2 CE1 CE2 CZ");if ($cen !=0){$cen=$index."\t".$cen;push(@centers, $cen);}}

elsif ($type eq "W")
	{
	$cen=get_average($refArr,"CD2 CE2 CE3 CZ2 CZ3 CH2");
	if ($cen !=0){$cen=$index."\t".$cen;push(@centers, $cen);}
	$cen1=get_coor_of_an_atom($refArr,"NE1");
	if ($cen1 !=0){$cen1=$index."\t".$cen1;push(@centers, $cen1);}
	}
elsif ($type eq "Y")
	{
	$cen=get_average($refArr,"CG CD1 CD2 CE1 CE2 CZ");
	if ($cen !=0){$cen=$index."\t".$cen;push(@centers, $cen);}
	 $cen1=get_coor_of_an_atom($refArr,"OH");
	if ($cen1 !=0){$cen1=$index."\t".$cen1;push(@centers, $cen1);}
	}

return @centers;
}
#-----------------------------------------------------------------------------------------#
#Given PDB lines (coordinates) of all atoms in a residue, output coordinates of certain atom.
sub get_coor_of_an_atom
{
my ($refArr, $atom)=@_;
my @array=@$refArr;
my $found=0;
foreach $array(@array)
	{
	chomp $array;
	if (trimLine(substr($array, 12,4)) eq $atom)
		{
		$coorLine=trimLine(substr($array, 30,8))."\t".trimLine(substr($array, 38,8))."\t".trimLine(substr($array, 46,8));
		$found=1;
		}
	}
if ($found ==1){return $coorLine;}
else {return $found;}
}
#------------------------------------------------------------------------------------------#
sub get_average
{
my ($refArr, $atomAll)=@_;
my @array=@$refArr;
my @tmp5=split(/\s+/, $atomAll);

my $sum_coorX=0;my $sum_coorY=0;my $sum_coorZ=0;
my $atom_number=0;
foreach $array(@array)
    {
    chomp $array;
    foreach $tmp5(@tmp5)
        {
		if (trimLine(substr($array, 12,4)) eq $tmp5)
			{
			$sum_coorX=$sum_coorX+ trimLine(substr($array, 30,8));
			$sum_coorY=$sum_coorY+ trimLine(substr($array, 38,8));
			$sum_coorZ=$sum_coorZ+ trimLine(substr($array, 46,8));
			$atom_number++;
			}
    	}
     }
# If atoms missing for a given residue, the residue is not calculated.
if ($atom_number==($#tmp5+1))
	{
	$sum_coorX=int(($sum_coorX/$atom_number)*1000)*0.001;
	$sum_coorY=int(($sum_coorY/$atom_number)*1000)*0.001;
	$sum_coorZ=int(($sum_coorZ/$atom_number)*1000)*0.001;
	$coorLine=$sum_coorX."\t".$sum_coorY."\t".$sum_coorZ;
	}
else {$coorLine=0;}
return $coorLine;
}
#------------------------------------------------------------------------------------------#
sub generate_vectors
{
my ($ptfFile, $ffFile)=@_;
system("featurize -P $ptfFile > $ffFile");
return 1;
}
#------------------------------------------------------------------------------------------#
sub threeLetterRes2oneLetter                                                                                               {
  $lineResidue3letter=$_[0];
  if( $lineResidue3letter =~ "ALA" ){ return "A"; }
  if( $lineResidue3letter =~ "CYS" ){ return "C"; }
  if( $lineResidue3letter =~ "ASP" ){ return "D"; }
  if( $lineResidue3letter =~ "GLU" ){ return "E"; }
  if( $lineResidue3letter =~ "PHE" ){ return "F"; }
  if( $lineResidue3letter =~ "GLY" ){ return "G"; }
  if( $lineResidue3letter =~ "HIS" ){ return "H"; }
  if( $lineResidue3letter =~ "ILE" ){ return "I"; }
  if( $lineResidue3letter =~ "LYS" ){ return "K"; }
  if( $lineResidue3letter =~ "LEU" ){ return "L"; }
  if( $lineResidue3letter =~ "MET" ){ return "M"; }
  if( $lineResidue3letter =~ "ASN" ){ return "N"; }
  if( $lineResidue3letter =~ "PRO" ){ return "P"; }
  if( $lineResidue3letter =~ "GLN" ){ return "Q"; }
  if( $lineResidue3letter =~ "ARG" ){ return "R"; }
  if( $lineResidue3letter =~ "SER" ){ return "S"; }
  if( $lineResidue3letter =~ "THR" ){ return "T"; }
  if( $lineResidue3letter =~ "VAL" ){ return "V"; }
  if( $lineResidue3letter =~ "TRP" ){ return "W"; }
  if( $lineResidue3letter =~ "TYR" ){ return "Y"; }
  return "X";
}
#------------------------------------------------------------------------------------------#
sub trimLine
{my ($line)=@_;chomp $line;$line=~s/^\s+//;$line =~ s/\s+$//;return $line;}
