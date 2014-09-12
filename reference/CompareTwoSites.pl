#! /usr/bin/perl
# Tianyun Liu 2011
# Stanford University
#=================================================================================================#
use List::MoreUtils qw(uniq);
#=================================================================================================#
if ($#ARGV != 4)
        {print "usage: write.pl pocket1 pocket2 STDFile(All1160Cavity.std) CutOffFile (TcCutoff4Normalize.txt) output\n";exit;}
my $file1=$ARGV[0];
my $file2=$ARGV[1];
my $stdFile=$ARGV[2];
my $cutFile=$ARGV[3];
my $output=$ARGV[4];
#=================================================================================================#
open (MYSTD, "<$stdFile")|| die "cannot open $stdFile\n"; my @line=<MYSTD>; close MYSTD;
chomp $line[0];my @std=split(/\t/, $line[0]); my $number_std=1;
#=================================================================================================#
my %cutoffType; #key: type; $value: distribution;
open (MYD, $cutFile)|| die "cannot open $cutFile"; my @cutoff=<MYD>;close MYD;
my @pairs=qw(); #72 allowed pairs
foreach $cutoff(@cutoff)
        {
        chomp $cutoff;
        my @tmp0=split(/\t/, $cutoff);
		push (@pairs, $tmp0[0]);
        $cutoffType{substr($cutoff, 0, 7)}=$tmp0[2];
        }
#=================================================================================================#
my @alignCutoff=(0, -0.15);
#=================================================================================================#
open (OUT, ">$output") || die "cannot open $output";close (OUT);
open (OUT, ">>$output") || die "cannot open $output";

my @scores=compareScores ($file1, $file2);

my $pocket1=$file1; $pocket1=~s/\.ff//;
my $pocket2=$file1; $pocket2=~s/\.ff//;

if ($#scores==-1){print OUT $pocket1."\t".$pocket1."\tNA\n";}

else
	{
	#print all S(Tc) between allowed pairs before alignments
	my $scoreFile=$pocket1."_".$pocket2.".score";
	open (TMPS, ">$scoreFile") || die "cannot open $scoreFile";close (TMPS);
    open (TMPS, ">>$scoreFile") || die "cannot open $scoreFile";
	foreach $scores(@scores) {print TMPS$scores."\n";}
	close TMPS;

	#alignments
	my @alignment=qw();
	@alignment=alignSite (\@scores);

	if ($#alignment== -1){print OUT $pocket1."\t".$pocket2."\tNA\n";}
	else
		{
		#print individual alignments (all alignments)
		my $alignFile=$pocket1."_".$pocket2.".align";
		open (TMPO, ">$alignFile") || die "cannot open $alignFile";close (TMPO);
		open (TMPO, ">>$alignFile") || die "cannot open $alignFile";
		foreach $alignment(@alignment){print TMPO $alignment."\n";}
		close TMPO;

		#print score of similarity
		$sumAligned=calculate_sum(\@alignment);
		@sum1=calculate_sum_above_cutoff(\@alignment,$alignCutoff[0]);
		@sum2=calculate_sum_above_cutoff(\@alignment,$alignCutoff[1]);

		my $totalComparable=$#scores+1; my $totalAligned=$#alignment+1;
        print OUT $pocket1."\t".$pocket2."\t".$totalComparable."\t";
		print OUT $totalAligned."\t".$sumAligned."\t".$sum1[0]."\t".$sum1[1]."\t".$sum2[0]."\t".$sum2[1]."\n";
		}
	}

close OUT;
#=================================================================================================#
sub compareScores
{
my ($ffFile1, $ffFile2)=@_;
open (FF1, $ffFile1) || die "cannot open $ffFile1\n"; my @ff1=<FF1>; close FF1;
open (FF2, $ffFile2) || die "cannot open $ffFile2\n"; my @ff2=<FF2>; close FF2;

my @Pscores=qw();
foreach $ff1(@ff1)
	{
	chomp $ff1; my $type1=substr($ff1, -5,3);
	foreach $ff2(@ff2)
		{
		chomp $ff2;my $type2=substr($ff2, -5,3);
		$testYes=CheckExistPairs($type1, $type2);
		if ($testYes ==1)
			{
			my $pairScore=calculate_tc_between_two_vector($ff1, $type1, $ff2,$type2 );
			push (@Pscores, $pairScore);
			}
		}
	}
return @Pscores;
}
#=================================================================================================#

sub calculate_tc_between_two_vector
{
my ($f1, $typeA, $f2,$typeB)=@_;
my @cou1=extract_property($f1);
my @cou2=extract_property($f2);
my $com=0;
my $all=0;
for ($t=0; $t<=$#cou1; $t++)
        {
		if(( $cou1[$t] !=0) || ($cou2[$t] !=0))
			{
        	$all++;
			if ((($cou1[$t] - $cou2[$t])>=0 ) && (($cou1[$t] - $cou2[$t])<=($number_std*$std[$t]))) {$com++;}
        	elsif ((($cou1[$t] - $cou2[$t])<0 ) && (($cou2[$t] - $cou1[$t])<=($number_std*$std[$t]))) {$com++;}
        	}
		}
# |+(X) n +(Y)| / (a - |+(X)| - |+(Y)|)
my $tc=$com/($all*2- $com); my $TcScore=roundNumber($tc);

#pair type
my $normal=calculate_normalized_score($tc, $typeA, $typeB);
my @tmpA=split(/\t/,$f1);my @tmpB=split(/\t/,$f2);
my $scoreLine=$tmpA[-1]."\t".$tmpB[-1]."\t".$TcScore."\t".$normal;
return $scoreLine ;
}
#=================================================================================================#
sub extract_property
{
my ($vector)=@_;
my @tmp=split(/\t/, $vector);
my @count=qw();
foreach ($t=1; $t<=480; $t++) {push (@count, $tmp[$t] );}
return @count;
}
#=================================================================================================#
sub CheckExistPairs
{
my ($tag1, $tag2)=@_;
my $tmp1=$tag1."_".$tag2; my $tmp2=$tag2."_".$tag1;
my $yes=0;
foreach $pairs(@pairs)
	{if (($pairs eq $tmp1) || ($pairs eq $tmp2)) {$yes=1;}}
return $yes;
}
#=================================================================================================#
sub calculate_normalized_score
{
my ($value, $typeA, $typeB)=@_;
if (exists $cutoffType{$typeA."_".$typeB})
	{
	my $ratio=$value/($cutoffType{$typeA."_".$typeB});
	my $score=2/(1+$ratio*$ratio)-1;
	my $Nscore=roundNumber($score);
	return $Nscore;
	}
elsif (exists $cutoffType{$typeB."_".$typeA})
	{
    my $ratio=$value/($cutoffType{$typeB."_".$typeA});
	my $score=2/(1+$ratio*$ratio)-1;
	my $Nscore=roundNumber($score);
    return $Nscore;
    }
else {print "check residue pairs ".$typeB."_".$typeA."\n"; return 0;}
}

#=================================================================================================#
sub roundNumber
{my $numberLong=@_[0]; my $numberShort=int($numberLong*1000); $numberShort=$numberShort/1000; return $numberShort;}

#=================================================================================================#
sub alignSite
{
my $refDis=$_[0];
my @dis=@$refDis;
my @residueSetA=qw();my @residueSetB=qw();

foreach $dis(@dis)
	{
	chomp $dis;my @tmp0=split(/\t/, $dis);
	push (@residueSetA, $tmp0[0]);
	push (@residueSetB, $tmp0[1]);
	}
my @setA=uniq(@residueSetA);my @setB=uniq(@residueSetB);

#find best scores (most negative ones) for each residue
my @alignedA=qw();
foreach $setA(@setA)
	{
	my @tmpLine=qw(); my %hashA;
	@tmpLine=grep (/$setA/, @dis);
	foreach $tmpLine(@tmpLine)
		{chomp $tmpLine; my @tmpScore=split(/\t/, $tmpLine); $hashA{$tmpScore[0].":".$tmpScore[1]}=$tmpScore[3];}
	# the most negative ones
	my @keys = sort { $hashA{$a} <=> $hashA{$b} } keys %hashA;
	push (@alignedA, $keys[0]."\t".$hashA{$keys[0]});
	}

my @alignedB=qw();
foreach $setB(@setB)
    {
    my @tmpLine=qw(); my %hashB;
    @tmpLine=grep (/$setB/, @dis);
    foreach $tmpLine(@tmpLine)
        {chomp $tmpLine; my @tmpScore=split(/\t/, $tmpLine); $hashB{$tmpScore[0].":".$tmpScore[1]}=$tmpScore[3];}
    # the most negative ones
    my @keys = sort { $hashB{$a} <=> $hashB{$b} } keys %hashB;
    push (@alignedB, $keys[0]."\t".$hashB{$keys[0]});
	}

#find overlap between %hashA and hashB: this can be calculated with some tolerance: eg, top 3, instead of top1.
my @aligned=qw();
foreach $alignedA(@alignedA)
	{
	my $found=0;
	foreach $alignedB(@alignedB){if ($alignedA eq $alignedB) {$found=1;}}
	if ($found ==1) {push (@aligned, $alignedA);}
	}
return @aligned;
}
#=================================================================================================#
sub calculate_sum
{
my ($ref)=@_;
my @array=@$ref;
my $ave=0;
foreach $array(@array)	{my @tmp=split(/\t/, $array); $ave=$ave+$tmp[-1];}
return $ave;
}

sub calculate_sum_above_cutoff
{
my ($ref, $cut)=@_;
my @array=@$ref;
my $ave=0;
my $number=0;
foreach $array(@array)
	{
	my @tmp=split(/\t/, $array);
	if ($tmp[-1]<=$cut){$number++; $ave=$ave+$tmp[-1];}
	}
my @line=qw(); push (@line, $number); push(@line, $ave);
return @line;
}

sub trimLine
{my ($line)=@_;chomp $line;$line=~s/^\s+//;$line =~ s/\s+$//;return $line;}
