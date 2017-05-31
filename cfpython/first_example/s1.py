import cf
f = cf.read('file.nc')
print('Type of file ', type(f))
print f

print('Properties: ', f.properties)
t=f.match('air_temperature', items={'latitude' : cf.gt(0)})
print(t)
print(f.array)

h = f.regrids(f, method='bilinear')
print(h)




#%matplotlib inline
import cfplot as cfp

cfp.con(h)


