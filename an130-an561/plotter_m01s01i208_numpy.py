import iris
import matplotlib.pyplot as plt
import iris.plot as iplt
import os
import iris.coord_categorisation
import numpy as np

# get the area average
def area_average(mycube, coord1, coord2):
    """
    Function that determines the area average
    Can be used with coord1 and coord2 (strings,
    usually 'longitude' and 'latitude' but depends on the cube);
    Returns a cube
    """
    import iris.analysis.cartography
    #mycube.coord(coord1).guess_bounds()
    #mycube.coord(coord2).guess_bounds()
    grid_areas = iris.analysis.cartography.area_weights(mycube)
    result = mycube.collapsed([coord1, coord2], iris.analysis.MEAN, weights=grid_areas)
    return result

######################################################
# stash - names
# surface temperature: m01s00i024
# precipitation flux: m01s05i216
# TOA Shortwave flux: m01s01i208
# TOA Longwave flux: m01s03i332
#######################################################
# select and merge cubes in years
# file type an561a.pm1981se.nc
rootdir = 'cfp_nc_an561_1208/'
years = ['1979','1980','1981','1982','1983','1984','1985','1986','1987','1988']
months = ['jan','feb','mar','apr','may','jun','jul','aug','se','oct','nov','dec']
cubeList1 = []
for yr in years:
    cubeList1y = []
    for mo in months:
        ff = 'an561a.pm' + yr + mo + '.nc'
        fp = rootdir + ff
        print('File: %s' % fp)
        if os.path.isfile(fp):
            c10 = iris.load_cube(fp)
            c10a = area_average(c10, 'longitude', 'latitude')
            cubeList1y.append(np.mean(c10a.data))
    cubeList1.append(np.mean(np.array(cubeList1y)))
#######################################################
# load cubes an130 and an561
# surface temperature m01s00i024
c1 = iris.load_cube('an130_apy_m01s01i208_global.nc')
#######################################################
# plotting
import numpy as np
fig = plt.figure()
plt.suptitle('m01s01i208 TOA Shortwave Flux an130-an561\nwith simple numpy.mean')
ax1 = fig.add_subplot(211)
ax1.plot([1979,1980,1981,1982,1983,1984,1985,1986,1987,1988],c1.data[0:10],label='an130')
ax1.plot([1979,1980,1981,1982,1983,1984,1985,1986,1987,1988],cubeList1,label='an561')
ax1.scatter([1979,1980,1981,1982,1983,1984,1985,1986,1987,1988],c1.data[0:10],label='an130')
ax1.scatter([1979,1980,1981,1982,1983,1984,1985,1986,1987,1988],cubeList1,marker='v',label='an561')
plt.ylabel('toa sw')
plt.xlim(1978,1989)
plt.grid()
plt.legend()
ax2 = fig.add_subplot(212)
dx = np.array(c1.data[0:10]) - np.array(cubeList1)
ax2.plot([1979,1980,1981,1982,1983,1984,1985,1986,1987,1988],dx,color='r')
ax2.scatter([1979,1980,1981,1982,1983,1984,1985,1986,1987,1988],dx,c='r')
plt.grid()
plt.ylabel('dtoa sw (an130 - an561)')
plt.xlabel('Time [years]')
plt.xlim(1978,1989)
plt.savefig('./plots/an130-an561_SW_m01s01i208_wNumpy.png')
plt.show()
plt.close()
