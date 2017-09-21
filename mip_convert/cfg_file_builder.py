# (C) British Crown Copyright 2015-2017, Met Office.
# Please see LICENSE.rst for license details.
# Author: Valeriu Predoi, University of Reading, September 2017

"""
Module that takes a set of configuration files (cfg) and adapts them
so any user can run mip_convert functional tests in a user directory.
Ultimately returns: path to cfg file, path to user test dir
"""

import os
import sys
import subprocess

def cfg_builder(d1, d2, d3, ancil_location, 
                cmor_tables_location):
    """
    Takes input variables and returns nested dict per
    cfg section and variable;
    Pass main sections and variables for each section
    d1: main root directory (on MO: /project/cdds)
    d2: main test root (on MO: testdata/functional_tests)
    d3: user test location (machine built by test_request as $HOME/$USER/mip_func_tests)
    """

    # initialize the nested dictionary
    cfg_file = {}

    # COMMON section
    cfg_file['COMMON'] = {}
    cfg_file['COMMON']['cdds_dir'] = d1
    cfg_file['COMMON']['root_test_location'] =  os.path.join(d1, d2)
    cfg_file['COMMON']['test_location'] = d3
    cfg_file['COMMON']['ancil_dir'] = ancil_location

    # CMOR setup
    cfg_file['cmor_setup'] = {}
    cfg_file['cmor_setup']['inpath'] = cmor_tables_location

    return cfg_file

def write_cfg_file(cfg_file, old_file):
    """
    Simple write-from-to-file function
    Overwrites a cfg file. in $USER's dir
    and NOT in the root test dir
    """
    import ConfigParser

    main_keys = cfg_file.keys()

    config = ConfigParser.RawConfigParser()

    # keep original font cases
    config.optionxform = str
    config.read(old_file)

    # start replacing in file
    for k in main_keys :
        for kk in cfg_file[k] :
            if kk == 'ancil_dir' :
                if config.has_option('COMMON','ancil_dir') :
                    anc_dir = config.get('COMMON', 'ancil_dir')
                    new_anc_dir = cfg_file[k][kk] + '/' + anc_dir.split('/')[-1]
                    config.set(k , 'ancil_dir', new_anc_dir)
            elif kk == 'inpath' :
                if k == 'cmor_setup' :
                    if config.has_option('cmor_setup','inpath') :
                        c_dir = config.get('cmor_setup', 'inpath')
                        new_c_dir = cfg_file[k][kk] + c_dir.split('}')[1]
                        config.set('cmor_setup' , 'inpath', new_c_dir)
            else:
                config.set(k , kk, cfg_file[k][kk])

    with open(old_file, 'wb') as configfile:
        config.write(configfile)

def get_root_tests(dirname):
    """
    Look up the root test directory and
    list its contents and subcontents
    """
    # empty lists to contain dir names and paths
    subdirs = []
    rpaths = []
    # capture the ls output
    lsd = 'ls -la ' + dirname
    proc = subprocess.Popen(lsd, stdout=subprocess.PIPE, shell=True)
    (out, err) = proc.communicate()
    res = out.split('\n')[3:-1]
    for sdout in res :
        subdir = sdout.split()[-1]
        rpath = os.path.join(dirname, subdir)
        if os.path.isdir(rpath) and subdir.startswith('test_') is True :
            subdirs.append(subdir)
            rpaths.append(rpath)

    return rpaths, subdirs

def prepare_test_cases(userpath, maindir, maintestdir, testcasedir, mipcfgdir, ancil_root, cmor_location) :
    """
    Replicates the test directory structure in user dir
    and migrates the cfg files and changes them as per user needs
    """
    paths = get_root_tests(mipcfgdir)[0]
    test_names = get_root_tests(mipcfgdir)[1]
    # lets create test directories in userpath (as root path)
    mastertestdir = os.path.join(userpath, testcasedir)
    mkrt = 'mkdir -p ' + mastertestdir
    proc = subprocess.Popen(mkrt, stdout=subprocess.PIPE, shell=True)
    (out, err) = proc.communicate()
    for r, s in zip(paths, test_names) :

        # each test
        testdir = os.path.join(mastertestdir, s)
        mkt = 'mkdir -p ' + testdir
        proc = subprocess.Popen(mkt, stdout=subprocess.PIPE, shell=True)
        (out, err) = proc.communicate()

        # each test subdir: data_out
        data_out = os.path.join(testdir, 'data_out')

        # build dirs
        mkdo = 'mkdir -p ' + data_out
        proc = subprocess.Popen(mkdo, stdout=subprocess.PIPE, shell=True)
        (out, err) = proc.communicate()

        # now that we have the structure,
        # let's get the cfg files to change them
        # accordingly to user
        cfgfilepath = os.path.join(r, 'etc/mip_convert.cfg')
        if os.path.isfile(cfgfilepath) :
            cpfile = 'cp ' + cfgfilepath + ' ' + data_out
            proc = subprocess.Popen(cpfile, stdout=subprocess.PIPE, shell=True)
            (out, err) = proc.communicate()

        # now we are ready to change the cfg file
        # set paths
        cfgfile = os.path.join(data_out, 'mip_convert.cfg')
        test_location = testdir
        ancil_location = ancil_root

        # change the file locally
        cfg_file_dict = cfg_builder(maindir, maintestdir, testdir, ancil_location, cmor_location)
        cfg_file = write_cfg_file(cfg_file_dict, cfgfile) 
        
    # returns: changed file path, path to all tests 
    return mastertestdir
