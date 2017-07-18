#!/usr/bin/env python
"""cstool.py: Script to split and join reads in input file."""
__author__ = "Matthias Hirsch-Hoffmann, Devang Mehta"
__copyright__ = "Copyright 2017, ETH Zuerich"
__version__ = "1.0.0"
__maintainer__ = "Matthias Hirsch-Hoffmann"
__email__ = "hirschhm@ethz.ch"
__status__ = "Production"
import sys,os
import click
import logging
import tempfile
import json
import glob
from Bio import SeqIO

@click.command()
#which arguments and options are needed? 
#arguments=mandatory, option=possible
#*************** ARGUMENETS *****************************
#action
@click.argument('action', type=click.Choice(['split','join','chart']))
#config-file
@click.argument('configfile', type=click.Path(exists=True,readable=True))
#input-file
@click.argument('inputfile', type=click.Path(exists=True,readable=True))

#*************** OPTIONS *****************************
#input-filetype
@click.option('--format', default='fasta', type=click.Choice(['fasta','fastq','tab','gb']), help='Input-file format (default=FASTA).')
@click.option('--numseq', default=1, type=click.INT , help='number of sequences per split-file.')
@click.option('--cluster', default='', type=click.STRING , help='Cluster command.')
@click.option('--clean', is_flag=True, help='will cleanup split folder.')

def main(action,configfile,inputfile,format,numseq,cluster,clean):
########################################################################################################								
	if action=='split':
		if not os.path.exists(inputfile+".dir"):
			os.makedirs(inputfile+".dir")
			i=0 #file-counter
			j=0 #sequence-counter
			outputfile=inputfile+".dir/"+os.path.basename(inputfile)+"."+str(i)+".fa"
			fout = open(outputfile,'wt')
			#process input file, sequence by sequence
			for record in SeqIO.parse(inputfile, format):
				#write sequence
				SeqIO.write(record,fout,'fasta')
				j+=1 #increase sequence-counter
				if j==numseq:
					#close file
					fout.close()
					output(outputfile,configfile,cluster)
					i+=1 #increase file-counter
					outputfile=inputfile+".dir/"+os.path.basename(inputfile)+"."+str(i)+".fa"
					fout = open(outputfile,'wt')
					j=0
				
			fout.close()
			output(outputfile,configfile,cluster)
			#create output of all filenames	as execution command e.g. python ./ciderseq.py <options> <configfile> <filename>  
		else:
			print('Output directory already exists. Use \'rm -rf '+inputfile+'.dir\' to remove split-target directory.')
########################################################################################################								
	elif action=='join':
		if not os.path.exists(inputfile+".dir"):
			print('Output directory missing.')
		else:
			#read config-file
			settings=config(configfile)
			#clean-up
			path=os.path.dirname(inputfile)
			fname=os.path.basename(inputfile)
			#identify genomes
			genomes=[]
			for genome in settings['phase']['phasegenomes']:
				genomes.append(genome)
##CLEANUP AND CREATION OF SUMMARY OUTPUT DIRECTORY #####################################################								
			#check outputdirectory
			if not os.path.isdir(path+"/"+settings['outputdir']):
				try:
					os.mkdir(path+"/"+settings['outputdir'])
				except:
					print("\nCould not create directory:"+path+"/"+settings['outputdir']+".\n")
					sys.exit(1)
			else:
				#cleanup
				cleanfile=path+"/"+settings['outputdir']+"/"+fname
				clean_join(cleanfile,['log'])
			#create summary folders
			steps=['separate','align','deconcat','annotate','phase']
			for step in steps:
				tmppath=path+"/"+settings[step]['outputdir']
				#check and create if necessary
				if not os.path.isdir(tmppath):
					try:
						os.mkdir(tmppath)
					except:
						print("\nCould not create directory:"+tmppath+".\n")
						sys.exit(1)
				else:
					#cleanup
					cleanfile=path+"/"+settings[step]['outputdir']+"/"+fname
					ftype=[]
					#clean up steps
					if step=='separate':
						ftype=['nohit.fa']
						for genome in genomes:
							ftype.append(genome+'.fa')
						clean_join(cleanfile,ftype)
					elif step=='align':
						for genome in genomes:
							ftype.append(genome+'.fa')
						clean_join(cleanfile,ftype)
					elif step=='deconcat':
						for genome in genomes:
							ftype.append(genome+'.fa')
							ftype.append(genome+'.stat')
						clean_join(cleanfile,ftype)
					elif step=='annotate':
						for genome in genomes:
							ftype.append(genome+'.json')
						clean_join(cleanfile,ftype)
					elif step=='phase':
						for genome in genomes:
							for fformat in settings[step]['outputformat']:
								ftype.append(genome+'.'+fformat)
						clean_join(cleanfile,ftype)
						
##COLLECT AND CREATE SUMMARY FILES #####################################################################								
			#collect all fasta files in split-directory, as we don't know how
			#many were created during split
			files=glob.glob(inputfile+".dir/*.fa")
			for ffile in files:
				#print(ffile)
				#set outputfilename
				fname=os.path.splitext(os.path.basename(ffile))[0]
				#print(fname)
				for step in steps:
					if step=='separate':
						join_text(inputfile,fname+".fa",settings,"log")
					elif step=='align':
						join_SeqIO(inputfile,fname,settings['separate'],'nohit.fa','fasta')
						for genome in genomes:
							join_SeqIO(inputfile,fname,settings['separate'],genome+'.fa','fasta')
					elif step=='deconcat':
						for genome in genomes:
							join_SeqIO(inputfile,fname,settings['deconcat'],genome+'.fa','fasta')
							join_text(inputfile,fname,settings['deconcat'],genome+'.stat')
					elif step=='annotate':
						for genome in genomes:
							join_json(inputfile,fname,settings['annotate'],genome+'.json')
					elif step=='phase':
						for genome in genomes:
							for fformat in settings['phase']['outputformat']:
								join_SeqIO(inputfile,fname,settings['phase'],genome+'.'+fformat,fformat)
### REMOVE SPLIT DIRECOTRY OF FLAG WAS SET #############################################################
			if clean:
				#remove split-directory
				for root, dirs, files in os.walk(inputfile+".dir", topdown=False):
				    for name in files:
				    	#print(os.path.join(root, name))
				        os.remove(os.path.join(root, name))
				    for name in dirs:
				    	#print(os.path.join(root, name))
				        os.rmdir(os.path.join(root, name))
				os.rmdir(inputfile+".dir")
########################################################################################################								
	elif action=='chart':
		import matplotlib
		matplotlib.use('Agg')
		import matplotlib.pyplot as plt
		#print('chart')
		#read config-file
		settings=config(configfile)
		#identify genomes
		genomes=[]
		for genome in settings['phase']['phasegenomes']:
			genomes.append(genome)
		#for every genome
		for g in genomes:
			############################ SEQUENCE LENGTH ###############################
			maxlength=0
			#original length
			olength=[]
			fname=os.path.dirname(inputfile)+"/"+settings['separate']['outputdir']+"/"+os.path.basename(inputfile)+"."+g+".fa"
			if os.path.isfile(fname):
				#read result file
				for record in SeqIO.parse(fname, 'fasta'):
					slen = len(record.seq)
					if slen > maxlength:
							maxlength=slen
					olength.append(slen)
			#deconcated length
			dlength=[]
			fname=os.path.dirname(inputfile)+"/"+settings['phase']['outputdir']+"/"+os.path.basename(inputfile)+"."+g+"."+settings['phase']['outputformat'][0]
			if os.path.isfile(fname):
				#read result file
				for record in SeqIO.parse(fname, settings['phase']['outputformat'][0]):
					slen = len(record.seq)
					if slen > maxlength:
							maxlength=slen
					dlength.append(slen)
			#define chart length and qty bins
			maxlength=(int(maxlength/200)+1)*200
			bins=maxlength/200
			
			fig, ax = plt.subplots()
			
			plt.xlabel('Sequence length')
			plt.ylabel('Number of sequences')
			plt.title('Sequence length before and after DeConcatenation: '+g)
			t=ax.hist([[olength],[dlength]] ,int(bins),histtype='bar', range=[0,maxlength],label=['before','after'])
			maxy=0
			for i in t[0]:
				if max(i) > maxy:
					maxy=max(i)+1
			ax.set_yticks(range(int(maxy)))
			ax.legend()
			plt.savefig(inputfile+'.seqlength.'+g+'.png')   # save the figure to file
			plt.close()		
		
		############################ Number Frameshifts ########################################
		#protein list
		proteins=[]
		#define result matrix
		for g in genomes:
			for k in sorted(settings['phase']['phasegenomes'][g]['proteins']):
				proteins.append(k)
		#print(proteins)
		#define result dict
		frameshift={}
		for k in sorted(proteins):	
			frameshift[k]=0
		#add value of qty sequences
		qty_seq=0
		#read annotation files
		for g in genomes:
			#generate filename
			fname=os.path.dirname(inputfile)+"/"+settings['annotate']['outputdir']+"/"+os.path.basename(inputfile)+"."+g+".json"
			#check if file exists
			if os.path.isfile(fname):
				#read json result file
				results={}
				with open(fname) as result_file:
					results=json.load(result_file)
					#loop through result
					for seq in results:
						for id in seq:
							complete=1
							reverted=0
							for k in sorted(settings['phase']['phasegenomes'][g]['proteins']):
								#print(k)
								if not k in seq[id]['proteins']: #check if protein from config exists in result
									complete=0 #incomplete - key missing
								elif not seq[id]['proteins'][k]['strand'] in [-1,1]:
									complete=0 #incomplete - contradicting strands
								else:
									#check strand and set reverse flag
									if int(seq[id]['proteins'][k]['strand']) != int(settings['phase']['phasegenomes'][g]['proteins'][k]['strand']):
										reverted+=1 #increase reverse, at the end reverse must have the length of proteins = reverse all 
						
							if complete==1 and (reverted==0 or reverted==len(settings['phase']['phasegenomes'][g]['proteins'])):
								qty_seq+=1
								for k in sorted(settings['phase']['phasegenomes'][g]['proteins']):		
									#print k, len(results[seq]['proteins'][k]['hsps'])-1
									frameshift[k]+=len(seq[id]['proteins'][k]['hsps'])-1

		fig, ax = plt.subplots()

		plt.xlabel('Protein')
		plt.ylabel('Number of frameshifts')
		plt.title('Number of frameshifts')

		y=[]
		for p in sorted(proteins):
			y.append(frameshift[p])
		
		ax.set_yticks(range(max(y)+1))
		ax.set_yticklabels(range(max(y)+1))
		ax.set_xticks(range(len(frameshift)))
		ax.set_xticklabels(sorted(proteins))
		ax.bar(range(len(frameshift)), y, 1/1.5)
		
		plt.savefig(inputfile+'.frameshift.png')   # save the figure to file
		plt.close()		

		############################ deconcat-stats ########################################
		#read the stats file
		for g in genomes:
			fname=os.path.dirname(inputfile)+"/"+settings['deconcat']['outputdir']+"/"+os.path.basename(inputfile)+"."+g+".stat"
			if os.path.isfile(fname):
				#read stat-file and process
				qtyseq=0
				deconcatrounds=[]
				for i in range(26):
					deconcatrounds.append(0)
				
				deconcatscores=[]
				deconcatcases={'1a':0,'1b':0,'1c':0,'1d':0,'2':0,'3':0,'4':0,'5':0}
				with open(fname) as ffile:
					for line in ffile:
						l=line.replace('\n','').split('\t')
						qtyseq+=1
						deconcatrounds[int(l[1])]+=1
						deconcatscores.append(float(l[2]))
						deconcatcases['1a']+=int(l[3])
						deconcatcases['1b']+=int(l[4])
						deconcatcases['1c']+=int(l[5])
						deconcatcases['1d']+=int(l[6])
						deconcatcases['2'] +=int(l[7])
						deconcatcases['3'] +=int(l[8])
						deconcatcases['4'] +=int(l[9])
						deconcatcases['5'] +=int(l[10])
				#rounds ###########################################################################
				fig, ax = plt.subplots()
				plt.xlabel('Number of DeConcat rounds')
				plt.ylabel('Number of sequences')
				plt.title(g)
				
				ax.set_yticks(range(max(deconcatrounds)+1))
				ax.set_xticks(range(26))
				ax.set_xticklabels(range(26))
				ax.bar(range(26), deconcatrounds, 1/1.5)
				
				plt.savefig(inputfile+'.deconcatrounds.'+g+'.png')   # save the figure to file
				plt.close()		
				#score ###########################################################################
				fig, ax = plt.subplots()
				plt.xlabel('Final DeConcat Score')
				plt.ylabel('Number of sequences')
				plt.title(g)

				ax.set_xticks(range(26))
				ax.set_xticklabels(range(26))

				t=ax.hist(deconcatscores ,26,histtype='bar',range=[0,25])

				maxy=0
				for i in t[0]:
					#print(i)
					if int(i) >= maxy:
						#print(i)
						maxy=(int(i)+1)
						#print('....'+str(maxy))

				ax.set_yticks(range(int(maxy)))
				ax.set_yticklabels(range(int(maxy)))

				plt.savefig(inputfile+'.deconcatscore.'+g+'.png')   # save the figure to file
				plt.close()		
				#cases ###########################################################################
				fig, ax = plt.subplots()
				plt.xlabel('Alignment Cases')
				plt.ylabel('Number of sequences')
				plt.title(g)

				x=[]
				for p in sorted(deconcatcases):
					x.append(p)
				y=[]
				for p in sorted(deconcatcases):
					y.append(deconcatcases[p])

				ax.set_yticks(range(max(y)+1))
				ax.set_yticklabels(range(max(y)+1))
				ax.set_xticks(range(len(deconcatcases)))
				ax.set_xticklabels(sorted(x))
				ax.bar(range(len(deconcatcases)), y, 1/1.5)

				plt.savefig(inputfile+'.deconcatcases.'+g+'.png')   # save the figure to file
				plt.close()		
		
########################################################################################################								
	else:
		print('ups...')

########################################################################################################								
def clean_join(inputfile,filetypes):
	#remove all existing summary files
	for ftype in filetypes:
		summaryfile=inputfile+"."+ftype
		#print('remove:'+summaryfile)
		if os.path.isfile(summaryfile):
			#remove file
			os.remove(summaryfile)
########################################################################################################								
def join_text(inputfile,fname,settings,fileext):
	resultfile=inputfile+".dir/"+settings['outputdir']+"/"+fname+"."+fileext
	#print(resultfile)
	if os.path.isfile(resultfile):
		#print('read')
		rf = open(resultfile,'r')
		data = rf.read()
		rf.close()
		summaryfile=os.path.dirname(inputfile)+"/"+settings['outputdir']+"/"+os.path.basename(inputfile)+"."+fileext
		#print(summaryfile)
		#print('write')
		sf = open(summaryfile,"at")
		sf.write(data)
		sf.close()
########################################################################################################								
def join_SeqIO(inputfile,fname,settings,fileext,filetype):
	resultfile=inputfile+".dir/"+settings['outputdir']+"/"+fname+"."+fileext
	if os.path.isfile(resultfile):
		summaryfile=os.path.dirname(inputfile)+"/"+settings['outputdir']+"/"+os.path.basename(inputfile)+"."+fileext
		#append to summary file
		with open(summaryfile, "at") as output_handle:
			##read result file
			for record in SeqIO.parse(resultfile, filetype):
				#write record to summary
				SeqIO.write(record, output_handle, filetype)	
########################################################################################################								
def join_json(inputfile,fname,settings,fileext):
	#dictionary for annotations to append and written at the end
	annotation=[] 
	#read summary file
	summaryfile=os.path.dirname(inputfile)+"/"+settings['outputdir']+"/"+os.path.basename(inputfile)+"."+fileext
	#print(summaryfile)
	if os.path.isfile(summaryfile):
		with open(summaryfile) as ffile:
			tmp=json.load(ffile)
			for r in tmp:
				annotation.append(r)
		ffile.close()
	#print(annotation)
	#append content of resultfile
	resultfile=inputfile+".dir/"+settings['outputdir']+"/"+fname+"."+fileext
	#print(resultfile)
	if os.path.isfile(resultfile):
		with open(resultfile) as ffile:
			tmp=json.load(ffile)
			for r in tmp:
				#print(r)
				annotation.append(r)
		ffile.close()
	#write new summary file
	fout = open(summaryfile,'wt') #write new
	#dump json output
	json.dump(annotation,fout)
	#close outputfile-handler
	fout.close()
########################################################################################################								
def config(configfile):
	#check config file
	if configfile is None:
		print("\nConfig file required.\n")
		sys.exit(1)
	#read configfile for output directroy
	settings={}
	with open(configfile) as config_file:
		try:
			settings=json.load(config_file)	
		except ValueError:
			print("\nError in config file.\n")
			sys.exit(1)
	return settings
########################################################################################################								
def output(outputfile,configfile,cluster):
	print(cluster +" \"",end='') if not cluster=='' else 0
	print("python ./ciderseq.py "+configfile+" "+outputfile,end='')
	print("\"",end='') if not cluster=='' else 0
	print()
########################################################################################################								
if __name__ == '__main__':
	
	main()

########################################################################################################								
