import iris
import matplotlib.pyplot as plt
import iris.plot as iplt
import os
import iris.coord_categorisation

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

def addtime(mycube):
    # add ayear as time coord
    newc1 = iris.coord_categorisation.add_month(mycube, 'time', name='month')
    newc = iris.coord_categorisation.add_year(newc1, 'time', name='year')
    return newc

# get the time average
def time_average(mycube):
    """
    Function to get the time average over MEAN;
    Returns a cube
    """
    var_mean = mycube.collapsed('time', iris.analysis.MEAN)
    return var_mean
# afterburner function
def spmean(cube, region=None):
    """
    Calculates the area-weighted spatial mean of the passed-in cube. By default
    the global mean is calculated. If a region is defined then the mean is
    calculated over the corresponding lat/long subset of the input cube.

    :param iris.cube.Cube cube: The cube for which to calculate the spatial mean.
    :param list region: If specified, defines the geographical region over which
        to calculate the area-weighted mean. The region should be a list of
        lat/long coordinates in the order: [min-long, min-lat, max-long, max-lat]
    :returns: A scalar cube containing the spatial mean.
    """
    # Ensure that lat/long coordinates have bounds.
    for coord_name in ['latitude', 'longitude']:
        coord = cube.coord(coord_name)
        if not coord.has_bounds(): coord.guess_bounds()

    if region:
        minlon, minlat, maxlon, maxlat = region[:]
        cube = cube.intersection(latitude=(minlat, maxlat), longitude=(minlon, maxlon))

    # Calculate grid weights.
    grid_weights = iris.analysis.cartography.area_weights(cube)

    # Calculate the spatial mean.
    mean_cube = cube.collapsed(['latitude', 'longitude'], iris.analysis.MEAN,
        weights=grid_weights)

    return mean_cube

# afterburner
def mkcg(cubelist):
    """
    Checks that all of the cubes in a cubelist are time contiguous. If one isn't
    then that cube is split into two at the break and the original cube is
    replaced in the cubelist by the two new ones. This function is then called
    recursively to check the new cubelist.
    """
    all_contiguous = True
    new_list = iris.cube.CubeList()

    for cube in cubelist:
        time_coord = cube.coord('time')
        if not time_coord.has_bounds():
            time_coord.guess_bounds()  # bounds will be contiguous by definition
            new_list.append(cube)
        elif time_coord.is_contiguous():
            new_list.append(cube)
        else:
            all_contiguous = False
            bounds = time_coord.bounds
            bi = 1
            while bi < len(bounds) and \
                  iris.util.approx_equal(bounds[bi,0], bounds[bi-1,1]):
                bi += 1
            if bi < len(bounds):
                bval = bounds[bi-1,1]
                earlier_constraint = iris.Constraint(time=lambda c, x=bval: c <= x)
                later_constraint = iris.Constraint(time=lambda c, x=bval: c > x)
                new_list.append(cube.extract(earlier_constraint))
                new_list.append(cube.extract(later_constraint))

    if not all_contiguous:
        new_list = _make_data_contiguous(new_list)

    return new_list
# afterburner
def prep(cubelist):
    from iris.experimental.equalise_cubes import equalise_attributes
    """
    Equalises the metadata in a cubelist to prepare the cubes for concatenation.
    It loops through the cubes in the cubelist and makes sure that variable and
    coordinate names are set correctly, that the cube is a vector rather than
    scalar along the time coordinate, and that any coordinates that won't
    concatenate have been removed.
    """
    # It's necessary to make a new list and add the cubes to this because if
    # the time axis is scalar then a new cube is created, which won't
    # then appear in the list
    new_list = iris.cube.CubeList()
    equalise_attributes(cubelist)
    for cube in cubelist:
        # read the data into memory or else the concatenation may not work
        _touch_data = cube.data

        # make sure that var_name is set
        if not cube.var_name:
            if cube.standard_name:
                cube.var_name = cube.standard_name
            elif 'STASH' in cube.attributes:
                cube.var_name = str(cube.attributes['STASH'])
            else:
                # replace any spaces with underscores
                cube.var_name = cube.name().replace(' ', '_').lower()

        # if the cube is scalar in time then add a time axis
        time_coord = cube.coord('time')
        if len(time_coord.points) == 1:
            cube = iris.util.new_axis(cube, 'time')

        # Make sure that the coordinate names are set correctly. Cubes loaded
        # from NetCDF will have coordinate names in unicode and so make sure
        # all are.
        for coord in cube.coords():
            try:
                coord.standard_name = unicode(coord.standard_name or '')
            except ValueError:
                coord.standard_name = u''
            coord.long_name = unicode(coord.long_name or '')
            if coord.var_name:
                coord.var_name = unicode(coord.var_name)
            else:
                coord.var_name = coord.standard_name

        # make sure that the circular flag is consistent on longitude
        cube.coord('longitude').circular = False

        # add the cube to the new cube list
        new_list.append(cube)

    return new_list
######################################################
# stash - names
# surface temperature: m01s00i024
# precipitation flux: m01s05i216
# TOA Shortwave flux: m01s01i208
# TOA Longwave flux: m01s03i332
#######################################################
# select and merge cubes in years
# file type an561a.pm1981se.nc
rootdir = 'cfp_nc_an561_5216/'
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
            cubeList1y.append(c10)
    cy1 = prep(mkcg(iris.cube.CubeList(cubeList1y)))
    fcy1 = cy1.concatenate_cube()
    fcy1a = spmean(fcy1)
    fnnc = '/group_workspaces/jasmin/ncas_cms/valeriu/an130_an561/m01s05i216_apy/' + str(yr) + '.nc'
    iris.save(fcy1a, fnnc)
    import numpy as np
    cubeList1.append(np.mean(fcy1a.data))
#######################################################
# load cubes an130 and an561
# surface temperature m01s00i024
c1 = iris.load_cube('an130_apy_m01s05i216_global.nc')
#######################################################
# plotting
import numpy as np
fig = plt.figure()
plt.suptitle('m01s05i216 Precipitation Flux an130-an561\nwith Afterburner functions')
ax1 = fig.add_subplot(211)
ax1.plot([1979,1980,1981,1982,1983,1984,1985,1986,1987,1988],c1.data[0:10],label='an130')
ax1.plot([1979,1980,1981,1982,1983,1984,1985,1986,1987,1988],cubeList1,label='an561')
ax1.scatter([1979,1980,1981,1982,1983,1984,1985,1986,1987,1988],c1.data[0:10],label='an130')
ax1.scatter([1979,1980,1981,1982,1983,1984,1985,1986,1987,1988],cubeList1,marker='v',label='an561')
plt.ylabel('PF')
plt.xlim(1978,1989)
plt.grid()
plt.legend()
ax2 = fig.add_subplot(212)
dx = np.array(c1.data[0:10]) - np.array(cubeList1)
ax2.plot([1979,1980,1981,1982,1983,1984,1985,1986,1987,1988],dx,color='r')
ax2.scatter([1979,1980,1981,1982,1983,1984,1985,1986,1987,1988],dx,c='r')
plt.grid()
plt.ylabel('dPF (an130 - an561)')
plt.xlabel('Time [years]')
plt.xlim(1978,1989)
plt.savefig('./plots/an130-an561_PF_m01s05i216_wAfterbFuncs.png')
plt.show()
plt.close()
