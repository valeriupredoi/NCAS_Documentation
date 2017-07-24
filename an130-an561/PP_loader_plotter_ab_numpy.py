import iris
import matplotlib.pyplot as plt
import subprocess
import time
import os
import numpy as np

# Functions
# get the area average
def area_average(mycube, coord1, coord2):
    """
    Function that determines the area average
    Can be used with coord1 and coord2 (strings,
    usually 'longitude' and 'latitude' but depends on the cube);
    Returns a cube
    """
    import iris.analysis.cartography
    # Boundaries are already in pp to NC generated files
    #mycube.coord(coord1).guess_bounds()
    #mycube.coord(coord2).guess_bounds()
    grid_areas = iris.analysis.cartography.area_weights(mycube)
    result = mycube.collapsed([coord1, coord2], iris.analysis.MEAN, weights=grid_areas)
    return result

######################################################
# Naming bit
# For an130 or an561 standardstash and var names
# surface temperature: m01s00i024
# precipitation flux: m01s05i216
# TOA Shortwave flux: m01s01i208
# TOA Longwave flux: m01s03i332
# Replace these as appropriate below -
######################################################
# In-situ parameters (these will be command-line options
# or parameter file entries)
# Change these lists as appropriate
# 1. root directory where monthly files live
rootdir = '/path/to/where/an130/was/run' + '/u-an130/'
# 2. simulation years
years = ['1978','1979','1980','1981','1982','1983','1984','1985','1986','1987','1988']
iyears = [int(a) for a in years]
# 3. numerical months
nr_months = ['01','02','03','04','05','06','07','08','09','10','11','12']
# 4. calendar months
months = ['jan','feb','mar','apr','may','jun','jul','aug','se','oct','nov','dec']
# 5. pp file name root
fileDescriptor = '*an130a.pm*'
# 6. Variable to be extracted stash code
stashCode = 'm01s00i024'
# 7. Dir to store monly NC files
ncFilesDir = 'NC_an130_' + stashCode + '/'
# 8. Afterburner-generated global yearly mean NC files per variable
afterburner_nc = 'an130_apy_m01s00i024_global.nc'
########################################################

# Running bit
# create NC files dir
if os.path.isdir(ncFilesDir) is False:
    mkc = 'mkdir -p ' + ncFilesDir
    proc = subprocess.Popen(mkc, stdout=subprocess.PIPE, shell=True)
    (out, err) = proc.communicate()

# Find PP files and load/convert to NC
for yr in years:
    for mo in nr_months:
        basedir = rootdir + yr + mo + '01T0000Z/'
        lf = 'ls  ' + basedir + fileDescriptor
        proc = subprocess.Popen(lf, stdout=subprocess.PIPE, shell=True)
        (out, err) = proc.communicate()
        fp = out.strip()
        print('PP file that we will extract variable from: %s' % fp)
        if os.path.isfile(fp):
            stash_cons_1 = iris.AttributeConstraint(STASH=stashCode)
            t1 = time.time()
            c10 = iris.load(fp, constraints=stash_cons_1)[0]
            frt = fp.split('/')[-1].strip('.pp')
            locf = ncFilesDir + frt + '.nc'
            iris.save(c10,locf)
            t2 = time.time()
            dt = t2-t1
            print('Time it took to load variable and convert to NC: %.1f' % dt)

# Read each of the NC files and get global yearly mean
cubeList1 = []
for yr in years:
    cubeList1y = []
    for mo in months:
        ff = 'an130a.pm' + yr + mo + '.nc'
        fp = ncFilesDir + ff
        print('NC file: %s' % fp)
        if os.path.isfile(fp):
            c10 = iris.load_cube(fp)
            c10a = area_average(c10, 'longitude', 'latitude')
            cubeList1y.append(np.mean(c10a.data))
    cubeList1.append(np.mean(np.array(cubeList1y)))

# load Afterburner-generated NC into cube
c1 = iris.load_cube(afterburner_nc)

# Plot
# the plot will have two panels:
# upper: plots an130 global year means for Afterburner and load/numpy methods
# lower: plots the delta between the two methods
fig = plt.figure()
ax1 = fig.add_subplot(211)
plt.suptitle('an130 - Afterburner/numpy comparison')
yrdx = len(iyears) - 1
ax1.plot(iyears,c1.data[0:yrdx],label='ab')
ax1.plot(iyears,cubeList1,label='numpy')
ax1.scatter(iyears,c1.data[0:yrdx],label='ab')
ax1.scatter(iyears,cubeList1,marker='v',label='numpy')
plt.ylabel('Variable')
xl1 = iyears[0] - 1
xl2 = iyears[-1] + 1
plt.xlim(xl1,xl2)
plt.grid()
plt.legend()
ax2 = fig.add_subplot(212)
dx = np.array(c1.data[0:yrdx]) - np.array(cubeList1)
ax2.plot(iyears,dx,color='r')
ax2.scatter(iyears,dx,c='r')
plt.grid()
plt.ylabel('delta (ab - numpy)')
plt.xlabel('Time [years]')
plt.xlim(xl1,xl2)
plt.show()
plt.close()
