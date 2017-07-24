import iris
import matplotlib.pyplot as plt
import iris.plot as iplt
import subprocess
import time
import os
import cf

######################################################
# an561
# loading with stash constraint
# surface temperature: m01s00i024
# precipitation flux: m01s05i216
# TOA Shortwave flux: m01s01i208
# TOA Longwave flux: m01s03i332
# basedir 19850601T0000Z
# file type
rootdir = '/group_workspaces/jasmin/ncas_cms/grenville/archive/u-an561/'
# beware of memory leakage causing a crash after five-six years
years = ['1978','1979','1980','1981','1982','1983','1984','1985','1986','1987','1988']
months = ['01','02','03','04','05','06','07','08','09','10','11','12']
cubeList1 = []#m01s00i024
cubeList2 = []#m01s05i216
cubeList3 = []#m01s01i208
cubeList4 = []#m01s03i332
for yr in years:
    cubeList1y = []#m01s00i024
    cubeList2y = []#m01s05i216
    cubeList3y = []#m01s01i208
    cubeList4y = []#m01s03i332
    for mo in months:
        basedir = rootdir + yr + mo + '01T0000Z/'
        lf = 'ls  ' + basedir + '*an561a.pm*'
        proc = subprocess.Popen(lf, stdout=subprocess.PIPE, shell=True)
        (out, err) = proc.communicate()
        fp = out.strip()
        print('File: %s' % fp)
        if os.path.isfile(fp):
            #stash_cons_1 = iris.AttributeConstraint(STASH='m01s00i024')
            #stash_cons_2 = iris.AttributeConstraint(STASH='m01s05i216')
            #stash_cons_3 = iris.AttributeConstraint(STASH='m01s01i208')
            #stash_cons_4 = iris.AttributeConstraint(STASH='m01s03i332')
            t1 = time.time()
            f=cf.read(fp)
            #g=f.select('surface_temperature',ndim=2)
            h=f.select('stash_code:3332',ndim=2)
            frt = fp.split('/')[-1].strip('.pp')
            locf = 'cfp_nc_an561_3332/' + frt + '.nc'
            cf.write(h, locf)
            t2 = time.time()
            dt = t2-t1
            print('Time per file: %.1f' % dt)





