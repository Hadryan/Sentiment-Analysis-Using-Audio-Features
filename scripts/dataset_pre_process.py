import numpy as np
import pandas as pd
import glob
import csv
import librosa
#import scikits.audiolab
import os
import subprocess
import json

def convert_sph( sph, wav ):
	command = ['sox','-t','sph', sph, '-b','16','-t','wav', wav]
	subprocess.check_call( command ) # Did you install sox (apt-get install sox)

data_parent_dir = "/scratch/nnejatis/pooya/NeMo-master/examples/asr/"
data_set_name = "TEDLIUM_release-3/data/"

ful_dir = data_parent_dir + data_set_name
stm_list = glob.glob(ful_dir + 'stm/*')
input_data = []
with open('data.json', 'w') as wri:
	for stmfilename in stm_list:
		print(stmfilename)
		with open(stmfilename, 'r') as f:
			lines = f.readlines()
			for line in lines:
				stm_line = line.split()	
				data = {}
				wave_file = ful_dir + 'sph/%s.sph.wav' % stm_line[0]
				data["audio_filepath"] = wave_file 
				data["duration"] = float(stm_line[4]) - float(stm_line[3])
				data["text"] = " ".join(stm_line[6:])
				wri.write(json.dumps(data)+"\n")
				input_data.append(data)

#with open('data.json', 'w') as f:
#	f.write( str(input_data) )

for stm in input_data:
	sph_file = stm['audio_filepath'][:-4]
	wave_file = stm['audio_filepath']
	if os.path.exists( sph_file ):
		if not os.path.exists( wave_file ):
			print(sph_file)
			convert_sph( sph_file, wave_file )
#		else:
#			print("wave file already exist")
	else:
		raise RuntimeError("Missing sph file from TedLium corpus at %s"%(sph_file))

   #with open(os.path.join(os.cwd(), filename), 'r') as f:
  
