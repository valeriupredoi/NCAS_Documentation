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
    """

    # initialize the nested dictionary
    cfg_file = {}

    # COMMON section
    cfg_file['COMMON'] = {}
    cfg_file['COMMON']['cdds_dir'] = d1 # where pp files live
    cfg_file['COMMON']['root_test_location'] =  d2 # root of testing
    cfg_file['COMMON']['test_location'] = d3 # actual test directory
    cfg_file['COMMON']['ancil_dir'] = ancil_location

    # CMOR setup
    cfg_file['cmor_setup'] = {}
    cfg_file['cmor_setup']['inpath'] = cmor_tables_location # where cmor lives; fullpath!
    #cfg_file['cmor_setup']['netcdf_file_action'] = 'CMOR_REPLACE_3'
    cfg_file['cmor_setup']['logfile'] = os.path.join(cfg_file['COMMON']['test_location'], 'cmor.log')
    #cfg_file['cmor_setup']['create_subdirectories'] = '0'

    # CMOR dataset
    #cfg_file['cmor_dataset'] = {}
    #cfg_file['cmor_dataset']['activity_id'] = activity_id
    #cfg_file['cmor_dataset']['branch_date_in_parent'] = 'test_time'
    #cfg_file['cmor_dataset']['branch_method'] = 'standard'
    #cfg_file['cmor_dataset']['calendar'] = '360_day'
    #cfg_file['cmor_dataset']['contact'] = 'emma.hogan@metoffice.gov.uk'
    #cfg_file['cmor_dataset']['experiment_id'] = 'rcp45'
    #cfg_file['cmor_dataset']['forcing_index'] = '1'
    #cfg_file['cmor_dataset']['further_info_url'] = 'http://furtherinfo.es-doc.org/mohc'
    #cfg_file['cmor_dataset']['grid'] = 'not checked'
    #cfg_file['cmor_dataset']['grid_label'] = 'gn'
    #cfg_file['cmor_dataset']['grid_resolution'] = '5 km'
    #cfg_file['cmor_dataset']['initialization_index'] = '1'
    #cfg_file['cmor_dataset']['institution'] = 'Met Office Hadley Centre, Fitzroy Road, Exeter, Devon, EX1 3PB, UK.'
    #cfg_file['cmor_dataset']['institution_id'] = 'MOHC'
    #cfg_file['cmor_dataset']['license'] = 'not checked'
    #cfg_file['cmor_dataset']['mip_era'] = mip_era
    #cfg_file['cmor_dataset']['outpath'] = os.path.join(cfg_file['COMMON']['test_location'], 'data_out')
    #cfg_file['cmor_dataset']['output_file_template'] = '<variable_id><table><source_id><experiment_id><variant_label>'
    #cfg_file['cmor_dataset']['parent_base_date'] = 'test_base_time'
    #cfg_file['cmor_dataset']['parent_experiment_id'] = exp
    #cfg_file['cmor_dataset']['parent_variant_label'] = ensemble
    #cfg_file['cmor_dataset']['physics_index'] = '1'
    #cfg_file['cmor_dataset']['realization_index'] = '1'
    #cfg_file['cmor_dataset']['source'] = source_docstring
    #cfg_file['cmor_dataset']['source_id'] = source_id
    #cfg_file['cmor_dataset']['source_type'] = source_type
    #cfg_file['cmor_dataset']['sub_experiment'] = 'not checked'
    #cfg_file['cmor_dataset']['sub_experiment_id'] = 'none'
    #cfg_file['cmor_dataset']['variant_info'] = 'N/A'
    #cfg_file['cmor_dataset']['variant_label'] = 'not checked'

    # request
    cfg_file['request'] = {}
    #cfg_file['request']['ancil'] = ancil_list #list
    #cfg_file['request']['base_date'] = base_date
    #cfg_file['request']['run_bounds'] = bounds_list #list of len 2
    cfg_file['request']['sourcedir'] = d1
    #cfg_file['request']['stream_ids'] = stream_ids #list
    #cfg_file['request']['suite_id'] = suite_id

    # variable
    #for stream_id in stream_ids :

    #    try :
    #        sapm = '[stream_' + stream_id + ']'
    #        argapm = mip_era + '_' + mip
    #        cfg_file[sapm][argapm] = variable
    #    except :
    #        print("stream_%s not a valid key" % stream_id)
    #        KeyError
    #        pass

    return cfg_file

def write_cfg_file(cfg_file, old_file):
    """
    Simple write-from-to-file function
    """
    import ConfigParser

    main_keys = cfg_file.keys()

    config = ConfigParser.RawConfigParser()
    config.read(old_file)

    # start replacing in file
    for k in main_keys :
        for kk in cfg_file[k] :
            if kk == 'ancil_dir' :
                if config.has_option('COMMON','ancil_dir') :
                    anc_dir = config.get('COMMON', 'ancil_dir')
                    new_anc_dir = cfg_file[k][kk] + '/' + anc_dir.split('/')[-1]
                    config.set(k , 'ancil_dir', new_anc_dir)
            elif kk == 'sourcedir' :
                if config.has_option('request','sourcedir') :
                    s_dir = config.get('request', 'sourcedir')
                    new_s_dir = cfg_file[k][kk] + '/' + s_dir.split('/')[-2] + '/' + s_dir.split('/')[-1]
                    config.set(k , 'sourcedir', new_s_dir)
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
    Look up the root tets directory and
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

def prepare_test_cases(userpath, roottestdir, ancil_root, cmor_location) :
    """
    Replicates the test directory structure in user dir
    and migrates the cfg files and changes them as per user needs
    """
    paths = get_root_tests(roottestdir)[0]
    test_names = get_root_tests(roottestdir)[1]
    # lets create test directories in userpath (as root path)
    mastertestdir = os.path.join(userpath, 'test_cases')
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
        cfg_file_dict = cfg_builder(roottestdir, userpath, testdir, ancil_location, cmor_location)
        cfg_file = write_cfg_file(cfg_file_dict, cfgfile) 
        
    # returns: changed file path, path to all tests 
    return cfgfile, mastertestdir

# test
#prepare_test_cases('/group_workspaces/jasmin/ncas_cms/valeriu/mip_convert_FT', '/group_workspaces/jasmin/ncas_cms/valeriu/mip_convert/mip_convert/tests/functional', '/group_workspaces/jasmin/ncas_cms/valeriu/mip_convert/mip_convert/tests/functional', '/group_workspaces/jasmin/ncas_cms/valeriu/mip_convert_test/cmor') 
