import matplotlib as mp
import matplotlib.pyplot as plt
import numpy as np
from glob import glob
import csv
import os

mp.rcParams['figure.figsize'] = 12, 4

dirs = glob('./*-*')
dirs = [dir for dir in dirs if os.path.isdir(dir)]
for dir in dirs:
	files = glob(dir + '/*.csv')
	for rising in [True, False]:
		last_time = 0
		first_time = 0
		part_name = dir[2:]
		rising_str = 'rising' if rising else 'falling'
		print(f'Processing {part_name} ({rising_str} edge) ', end='', flush=True)
		for file in files:
			print('.', end='', flush=True)
			with open(file, newline='') as csvfile:
				reader = csv.reader(csvfile, delimiter=',')
				points = list(map(lambda a: [float(a[0]), float(a[1])], list(reader)[3:]))
				xpos = list(map(lambda p: p[0], points))
				ypos = list(map(lambda p: p[1], points))
				if (rising and (np.average(ypos[0:100]) < 1)) or ((not rising) and (np.average(ypos[0:100]) > 3)):
					first_high_idx = 0
					if rising:
						first_high_idx = next(i for i, val in enumerate(ypos, 1) if val > 1)
						last_high_idx = len(ypos) - next(i for i, val in enumerate(reversed(ypos), 1) if val < 4)
					else:
						first_high_idx = next(i for i, val in enumerate(ypos, 1) if val < 4)
						last_high_idx = len(ypos) - next(i for i, val in enumerate(reversed(ypos), 1) if val > 1)					
					first_time = min(first_time, xpos[first_high_idx])
					last_time = max(last_time, xpos[last_high_idx])
					plt.plot(xpos, ypos, color='b', alpha=0.2)
		print('.', flush=True)
		plt.plot([0,0], [-0.25, 5.25], 'm--')
		plt.xlabel('Time (ms)')
		plt.ylabel('Voltage (V)')
		first_time = first_time - (first_time % 0.25)
		last_time = last_time - (last_time % 0.25) + 0.25
		plt.xlim(first_time - 0.25, last_time + 0.25)
		plt.title(f'{part_name} ({rising_str} edge)')
		file_name = f'{part_name}_{rising_str}.png'
		plt.tight_layout()
		plt.savefig(file_name)
		plt.clf()
