import numpy as np
import pandas as pd
import matplotlib as mp
import matplotlib.pyplot as plt
from glob import glob
import os

mp.rcParams['figure.figsize'] = 12, 4

IN_SAMP_RATE = 8.93e6
OUT_SAMP_RATE = 10e6
TIME_SCALE = 1e-3

# turn points into PWL points, minimising the point count where possible
# this eliminates consecutive points where their gradients are within some defined tolerance
def minimise_pwl(xp, yp, m_tol=0.5):
	out_x = [xp[0]]
	out_y = [yp[0]]
	last_idx = 0
	last_x = xp[0]
	last_y = yp[0]
	last_m = (yp[1] - yp[0]) / (xp[1] - xp[0])
	for i in range(1, len(xp)):
		m = (yp[i] - last_y) / (xp[i] - last_x)
		dm = abs(m - last_m)
		if dm > m_tol:
			# exceeded tolerance, emit point
			if last_idx < (i - 1):
				out_x.append(xp[i-1])
				out_y.append(yp[i-1])
			out_x.append(xp[i])
			out_y.append(yp[i])
			last_idx = i
			last_m = m
			last_x = xp[i]
			last_y = yp[i]
	if last_idx < len(xp) - 1:
		out_x.append(xp[-1])
		out_y.append(yp[-1])
	return np.array(out_x), np.array(out_y)

dirs = glob('./csv/*-*')
dirs = [dir for dir in dirs if os.path.isdir(dir)]
for dir in dirs:
	part_name = dir[6:]
	if not os.path.isdir('./pwl/' + part_name):
		os.mkdir('./pwl/' + part_name)
	files = glob(dir + '/*.csv')
	n = 0
	print(f'Processing {part_name} ', end='', flush=True)
	for file in files:
		print('.', end='', flush=True)
		# read source data into dataframe
		df = pd.read_csv(file, header=[0,1], dtype={'Time': np.float64, 'Channel A': np.float64})
		# two headers so flatten them and rename
		df.columns = df.columns.to_flat_index()
		df.rename(columns={df.columns[0]: 'Time', df.columns[1]: 'Voltage'}, inplace=True)
		# normalise timescale from ms to s
		df['Time'] *= TIME_SCALE
		# normalise data
		min_val = np.min(df['Voltage'])
		max_val = np.max(df['Voltage'])
		min_time = np.min(df['Time'])
		max_time = np.max(df['Time'])
		scale = max_val - min_val
		v_norm = ((df['Voltage'] - min_val) / scale) * max_val
		# linearly interpolate to a fixed round sample rate
		samp_count = int((OUT_SAMP_RATE / IN_SAMP_RATE) * len(v_norm))
		space = np.linspace(min_time, max_time, samp_count)
		sig = np.interp(space, df['Time'], df['Voltage'])
		# clamp and rescale to get rid of noise (from the PSU/scope, not the switch)
		sig = np.maximum(sig, 0.1)
		sig = np.minimum(sig, 4.9)
		sig = (sig - 0.1) * (5.0/4.8)
		# figure out where the interesting bit happens (first and last rising/falling edge)
		start_index = max(np.argwhere(sig<4.95)[0][0], np.argwhere(sig>0.05)[0][0])
		end_index = min(len(sig) - np.argwhere(np.flip(sig)>0.05)[0][0] - 1, len(sig) - np.argwhere(np.flip(sig)<4.95)[0][0] - 1)
		# is the switch opening or closing?
		closing = np.mean(sig[:100]) < 1.5
		closing_str = "CLOSING" if closing else "OPENING"
		# margins before/after the area of interest
		pre_gap = 1e-4
		post_gap = 1e-4
		start_index = max(0, start_index - int(OUT_SAMP_RATE*pre_gap))
		end_index = min(len(sig) - 1, end_index + int(OUT_SAMP_RATE*post_gap))
		start_time = space[start_index]
		end_time = space[end_index]
		# crop the space and data to the area of interest
		space = space[start_index:end_index]
		sig = sig[start_index:end_index]
		space -= start_time
		# minimise the points using PWL
		pwl_x, pwl_y = minimise_pwl(space, sig)
		# graphs if you want
		#plt.plot(df['Time'], df['Voltage'], 'r')
		#plt.plot(space, sig, 'b')
		#plt.plot(pwl_x, pwl_y, 'g')
		#plt.xlim(start_time, end_time)
		#plt.show()
		# add a point waaaaaaaaaaaaaay off in the future so the output effectively goes constant afterwards
		pwl_x = np.append(pwl_x, 1e9)
		pwl_y = np.append(pwl_y, pwl_y[-1])
		# original data is for 5V so normalise to 1V
		pwl_y *= 0.2
		# assuming 10k pulldown, what would the upper resistance have been?
		# this gets us a resistance value where Roff=100Meg and Ron=1m
		pwl_y = (1e4/(pwl_y+100e-6)) - 1e4 + 1e-3
		# turn the results into a dataframe and save
		df_out = pd.DataFrame({'Time': pwl_x, 'Voltage': pwl_y})
		df_out.to_csv(f'./pwl/{part_name}/{part_name}_{n:03d}_{closing_str}.txt', sep="\t", header=False, index=False)
		n += 1
	print(".")
