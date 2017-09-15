#!/bin/bash
CMOR_VERSION="3.2.5"
CDDS_DIR=$(pwd)
CDDS_PACKAGES="extract hadsdk mip_convert transfer"
SOFTWARE_PREFIX=~support/software
SOFTWARE_SUFFIX=lib/python2.7/site-packages

# Use the SciTools install and Iris 1.10.0:
PYTHON_BIN=/usr/local/sci/bin
IRIS_LIB=$SOFTWARE_PREFIX/iris-1.10.0
export PATH=$PYTHON_BIN:$PATH
export PYTHONPATH=$IRIS_LIB:$PYTHONPATH

# Use the Scientific Software Stack (current = 2017_06_07; Iris 1.13.0):
#module load scitools/default-current
#CMOR_VERSION=${CMOR_VERSION}_Python-2.7.12

# Update PATH:
for CDDS_PACKAGE in $CDDS_PACKAGES
do
    if [ -d $CDDS_DIR/$CDDS_PACKAGE/bin ]; then
        export PATH=$CDDS_DIR/$CDDS_PACKAGE/bin:$PATH
    fi
done

# Update PYTHONPATH:
CMOR_LIB=$SOFTWARE_PREFIX/cmor-$CMOR_VERSION/$SOFTWARE_SUFFIX
MYSQLDB_LIB=$SOFTWARE_PREFIX/$SOFTWARE_SUFFIX
export PYTHONPATH=$CMOR_LIB:$MYSQLDB_LIB:$PYTHONPATH
for CDDS_PACKAGE in $CDDS_PACKAGES
do
    if [ -d $CDDS_DIR/$CDDS_PACKAGE ]; then
        export PYTHONPATH=$CDDS_DIR/$CDDS_PACKAGE:$PYTHONPATH
    fi
done

# Update LD_LIBRARY_PATH:
UUID_LIB=$SOFTWARE_PREFIX/lib
export LD_LIBRARY_PATH=$UUID_LIB:$LD_LIBRARY_PATH
