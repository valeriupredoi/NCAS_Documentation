# (C) British Crown Copyright 2015-2017, Met Office.
# Please see LICENSE.rst for license details.
# pylint: disable = missing-docstring, invalid-name, too-many-public-methods
# pylint: disable = no-member, no-value-for-parameter
"""
Tests for request.py.
"""
import argparse
from datetime import datetime
from io import BytesIO
import logging
from mock import call, patch
from nose.plugins.attrib import attr
import os
import StringIO
import subprocess
import sys
from textwrap import dedent
import unittest

from mip_convert import configuration as cfg
from mip_convert import request
from mip_convert.request import (
    LOG_NAME, LOG_LEVEL, parse_parameters, main, get_model_to_mip_mappings,
    get_mip_table, get_variable_model_to_mip_mapping, get_requested_variables)
from mip_convert.save.cmor.cmor_outputter import (CmorGridMaker,
                                                  AbstractAxisMaker)

import cfg_file_builder as cfb

DEBUG = False
NCCMP_TIMINGS = []


class TestParseParameters(unittest.TestCase):
    """
    Tests for ``parse_parameters`` in request.py.
    """

    def setUp(self):
        self.config_file = 'my_mip_convert.cfg'
        self.run_bounds = '1950-03-10-00-00-00 1950-03-20-00-00-00\n'

    @patch('os.path.isfile')
    def test_correct_argparse_namespace(self, misfile):
        misfile.return_value = True
        parameters = parse_parameters([self.config_file])
        misfile.assert_called_once_with(parameters.config_file)
        self.assertIsInstance(parameters, argparse.Namespace)
        self.assertEquals(parameters.config_file, self.config_file)
        self.assertEquals(parameters.log_name, LOG_NAME)
        self.assertEquals(parameters.append_log, False)
        self.assertEquals(parameters.log_level, LOG_LEVEL)

    @patch('os.path.isfile')
    def test_correct_log_name_value(self, misfile):
        # log_name can be set using --log_name.
        misfile.return_value = True
        reference = 'my_log.txt'
        parameters = parse_parameters(
            [self.config_file, '--log_name', reference])
        misfile.assert_called_once_with(parameters.config_file)
        self.assertEquals(parameters.log_name, reference)

    @patch('os.path.isfile')
    def test_correct_append_log_value(self, misfile):
        # append_log can be set to True using -a (it is False by
        # default).
        misfile.return_value = True
        parameters = parse_parameters([self.config_file, '-a'])
        misfile.assert_called_once_with(parameters.config_file)
        reference = True
        self.assertEquals(parameters.append_log, reference)

    @patch('os.path.isfile')
    def test_correct_verbose_value(self, misfile):
        # verbose can be set to True using --verbose (it is False
        # by default). This sets log_level to logging.DEBUG.
        misfile.return_value = True
        parameters = parse_parameters([self.config_file, '--verbose'])
        misfile.assert_called_once_with(parameters.config_file)
        reference = logging.DEBUG
        self.assertEquals(parameters.log_level, reference)

    @patch('os.path.isfile')
    def test_correct_quiet_value(self, misfile):
        # quiet can be set to True using -q (it is False by default).
        # This sets log_level to logging.WARNING.
        misfile.return_value = True
        parameters = parse_parameters([self.config_file, '-q'])
        misfile.assert_called_once_with(parameters.config_file)
        reference = logging.WARNING
        self.assertEquals(parameters.log_level, reference)

    def test_missing_user_config_file(self):
        # parse_parameters raises an exception if the 'user
        # configuration file' does not exist.
        config_file = 'random_file'
        parameters = [config_file]
        self.assertRaises(IOError, parse_parameters, parameters)


class TestMain(unittest.TestCase):
    """
    Tests for ``main`` in request.py.
    """

    def setUp(self):
        # as it is now dirname is where this file lives
        # suggest setting a dedicated 'functional' test directory
        # dirname = path/to/functional
        dirname = os.path.dirname(os.path.realpath(__file__))
        ##########################################
        # Centralizing functional tests on JASMIN
        ##########################################
        # setup assumes the following:
        # - (dirname) is master test directory where this file lives;
        # - (dirname)/functional contains:
        #   - multiple test dirs e.g. test_CMIP5_Amon_va... (data_dir);
        #   - one input(set1:pp,set2:pp, set3:pp) dir;
        #   - each (data_dir) has one reference_dir(with a netCDF file);
        #   - each (data_dir) has one etc(with a mip_convert.cfg that will be 
        #     changed to suit the user test);
        ancil_root = '/project/cdds' # hardcode this accordingly
        cmor_files = 'full/path/to/cmor_files' # hardcode this accordingly
        self.config_base_path = os.path.join(dirname, 'functional')
        #self.data_base_path = (
        #    '/project/cdds/testdata/diagnostics/test_cases/')
        self.out_base_path = cfb.prepare_test_cases('home/user/path', self.config_base_path, ancil_root, cmor_files)[1]
        self.compare_netcdf = (
            'nccmp -dmgfbi {tolerance} {history} {options} '
            '--globalex=cmor_version,creation_date,data_specs_version,'
            'table_info,tracking_id,_NCProperties {output} {reference}')
        self.input_dir = 'test_{}_{}_{}'

    def tearDown(self):
        CmorGridMaker._GRID_CACHE = dict()
        AbstractAxisMaker.axis_cache = dict()

    def convert(self, input_dir, output_dir, reference_dir, filenames):
        #config_file = os.path.join(
        #    self.config_base_path, input_dir, 'etc', 'mip_convert.cfg')
        config_file = cfb.prepare_test_cases('home/user/path', self.config_base_path, ancil_root, cmor_files)[0]
        #data_dir = os.path.join(self.data_base_path, input_dir)
        #log_name = os.path.join(data_dir, 'mip_convert.log')
        #output_dir = os.path.join(data_dir, output_dir)
        data_dir = os.path.join(self.config_base_path, input_dir)
        output_dir = os.path.join(self.out_base_path, input_dir, output_dir)
        log_name = os.path.join(output_dir, 'mip_convert.log')
        outputs = [os.path.join(output_dir, filename) for
                   filename in filenames]
        test_reference_dir = os.path.join(data_dir, reference_dir)
        references = [os.path.join(test_reference_dir, filename) for
                      filename in filenames]
        # Provide help if the reference file does not exist.
        for reference in references:
            if not os.path.isfile(reference):
                print 'Reference file does not exist'
        # Remove the output file from the output directory.
        for output in outputs:
            if os.path.isfile(output):
                os.remove(output)
        # Ignore the Iris warnings sent to stderr by main().
        orig_stderr = sys.stderr
        sys.stderr = StringIO.StringIO()
        parameters = [config_file, '-q', '-l', log_name]
        # Set the umask so all files produced by 'main' have read and write
        # permissions for all users.
        orig_umask = os.umask(000)
        return_code = main(parameters)
        os.umask(orig_umask)
        sys.stderr = orig_stderr
        if return_code == 1:
            raise RuntimeError(
                'MIP Convert failed. Please check "{}"'.format(log_name))
        # Provide help if the output file does not exist.
        for output in outputs:
            if not os.path.isfile(output):
                output_dir_contents = os.listdir(output_dir)
                if not output_dir_contents:
                    print ('Output file not created. Please check '
                           '"{data_dir}/cmor.log"'.format(data_dir=data_dir))
                else:
                    if len(output_dir_contents) == 1:
                        output_dir_contents = output_dir_contents[0]
                    print (
                        'CMOR did not create the correctly named output file; '
                        'output directory contains "{output_dir_contents}"'
                        ''.format(output_dir_contents=output_dir_contents))
        return outputs, references

    def compare_command(self, outputs, references, tolerance_value=None,
                        ignore_history=False, other_options=None):
        tolerance = ''
        if tolerance_value is not None:
            tolerance = '--tolerance={tolerance_value}'.format(
                tolerance_value=tolerance_value)
        history = ''
        if ignore_history:
            history = '--Attribute=history'
        options = ''
        if other_options is not None:
            options = other_options
        compare_commands = [
            self.compare_netcdf.format(
                tolerance=tolerance, history=history, options=options,
                output=output, reference=reference).split() for
            output, reference in zip(outputs, references)]
        return compare_commands

    def compare(self, compare_commands):
        differences = []
        start_time = datetime.now()
        for compare_command in compare_commands:
            print 'Running compare command:', ' '.join(compare_command)
            process = subprocess.Popen(compare_command, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
            # The communicate() method returns a tuple in the form
            # (stdoutdata, stderrdata).
            differences.append(process.communicate())
            # From the nccmp help: "Exit code 0 is returned for
            # identical files, 1 for different files, and 2 for a fatal
            # error". In addition, process.returncode = -11 when a
            # segmentation fault occurs.
            if process.returncode < 0 or process.returncode == 2:
                raise AssertionError(
                    'Problem running comparison command: {compare_command}'
                    ''.format(compare_command=' '.join(compare_command)))
        end_time = datetime.now()
        duration = end_time - start_time
        NCCMP_TIMINGS.append(duration.total_seconds())
        number_of_tests = len(
            [test for test in dir(self) if test.startswith('test')])
        if len(NCCMP_TIMINGS) == number_of_tests:
            print 'nccmp took {:.3}s'.format(sum(NCCMP_TIMINGS))
        if DEBUG:
            stdoutdata = [output[0] for output in differences]
            print stdoutdata
        # If there are any differences, nccmp sends output to
        # STDERR.
        stderrdata = [output[1] for output in differences]
        self.assertEqual(set(stderrdata), set(['']))

    # Fails because of 'out-of-bounds adjustments' in history.
    # @attr('slow')
    # def test_um_atmosphere_pp_n216_3d_pr(self):
    #     anyqb, apa, 360_day, (lat, lon, time).
    #     input_dir = self.input_dir.format('CMIP5', 'day', 'pr_N216')
    #     outputs, references = self.convert(
    #         input_dir 'data_out', 'reference_output',
    #         ['pr_day_HadGEM2-ES_rcp85_r1i1p1f1_19310101-19310130.nc'])
    #     self.compare(self.compare_command(
    #         outputs, references, tolerance_value='4e-5'))

    @attr('slow')
    def test_um_atmosphere_pp_monthly_3d_sbl(self):
        # ajnjg, 360_day, (lat, lon, time).
        input_dir = self.input_dir.format('CMIP5', 'Amon', 'sbl')
        outputs, references = self.convert(
            input_dir, 'data_out', 'reference_output',
            ['sbl_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc'])
        self.compare(
            self.compare_command(outputs, references, ignore_history=True))

    @attr('slow')
    def test_um_atmosphere_pp_monthly_3d_sconcdust_lblev(self):
        # u-an644, 360_day, (lat, lon, time).
        input_dir = self.input_dir.format('CMIP6', 'Emon', 'sconcdust')
        outputs, references = self.convert(
            input_dir, 'data_out', 'reference_output',
            ['sconcdust_Emon_UKESM1-0-LL_amip_r1i1p1f1_gn_197904-197904.nc'])
        self.compare(
            self.compare_command(outputs, references, ignore_history=True))

    @attr('slow')
    def test_um_atmosphere_pp_monthly_heaviside_pressure_levels_4d_ta(self):
        # ajnjg, 360_day, (lat, lon, time, plevs).
        input_dir = self.input_dir.format('CMIP5', 'Amon', 'ta')
        outputs, references = self.convert(
            input_dir, 'data_out', 'reference_output',
            ['ta_Amon_HadGEM2-A_amip_r1i1p1f1_202109-202109.nc'])
        self.compare(
            self.compare_command(outputs, references, ignore_history=True))

    @attr('slow')
    def test_um_atmosphere_pp_monthly_heaviside_pressure_levels_4d_va(self):
        # ajnjg, 360_day, (lat, lon, time, plevs).
        input_dir = self.input_dir.format('CMIP5', 'Amon', 'va')
        outputs, references = self.convert(
            input_dir, 'data_out', 'reference_output',
            ['va_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc'])
        self.compare(
            self.compare_command(outputs, references, ignore_history=True))

    # @attr('slow')  #110
    # def test_um_atmosphere_pp_monthly_time_series_4d_tas(self):
    #     # akpcd, 360_day, (site, time1, height2m).
    #     input_dir = self.input_dir.format('CMIP5', 'CFsubhr', 'tas')
    #     output, reference = self.convert(
    #         input_dir, 'data_out', 'reference_output',
    #         ['tas_CFsubhr_HadGEM2-ES_rcp45_r1i1p1f1_'
    #          '19781201000000-19781230232959.nc'])
    #     self.compare(
    #         self.compare_command(output, reference, ignore_history=True))

    # @attr('slow')  #110
    # def test_um_atmosphere_pp_monthly_time_series_4d_ta(self):
    #     # akpcd, 360_day, (site, time1, hybrid_height).
    #     input_dir = self.input_dir.format('CMIP5', 'CFsubhr', 'ta')
    #     output, reference = self.convert(
    #         input_dir, 'data_out', 'reference_output',
    #         ['ta_CFsubhr_HadGEM2-ES_rcp45_r1i1p1f1_'
    #          '19781201000000-19781230232959.nc'])
    #     self.compare(
    #         self.compare_command(output, reference))

    # @attr('slow')  #110
    # def test_um_atmosphere_pp_monthly_time_series_4d_rlucs(self):
    #     # akpcd, 360_day, (site, time1, hybrid_height).
    #     input_dir = self.input_dir.format('CMIP5', 'CFsubhr', 'rlucs')
    #     output, reference = self.convert(
    #         input_dir, 'data_out', 'reference_output',
    #         ['rlucs_CFsubhr_HadGEM2-ES_rcp45_r1i1p1f1_20081101000000-'
    #          '20081130210000.nc'])
    #     self.compare(
    #         self.compare_command(output, reference))

    # @attr('slow')  # 275
    # def test_um_land_pp_monthly_pseudo_level_4d_baresoilFrac_CMIP6(self):
    #     # u-an644, 360_day, (lat, lon, time, pseudo_level).
    #     input_dir = self.input_dir.format('CMIP6', 'Lmon', 'baresoilFrac')
    #     outputs, references = self.convert(
    #         input_dir, 'data_out', 'reference_output',
    #         ['baresoilFrac_Lmon_UKESM1-0-LL_amip_gn_r1i1p1f1_'
    #          '197904-197904.nc'])
    #     self.compare(
    #         self.compare_command(outputs, references))

    # @attr('slow')  # 275
    # def test_um_land_pp_monthly_pseudo_level_4d_baresoilFrac_CMIP5(self):
    #     # ajnjg, 360_day, (lat, lon, time, pseudo_level).
    #     input_dir = self.input_dir.format('CMIP5', 'Lmon', 'baresoilFrac')
    #     outputs, references = self.convert(
    #         input_dir, 'data_out', 'reference_output',
    #         ['baresoilFrac_Lmon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc'])
    #     self.compare(
    #         self.compare_command(outputs, references, ignore_history=True))

    # @attr('slow')  # 275
    # def test_um_land_pp_monthly_3d_grassFrac(self):
    #     # ajnjg, 360_day, (lat, lon, time), uses pseudo levels.
    #     input_dir = self.input_dir.format('CMIP5', 'Lmon', 'grassFrac')
    #     outputs, references = self.convert(
    #         input_dir, 'data_out', 'reference_output',
    #         ['grassFrac_Lmon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc'])
    #     self.compare(
    #         self.compare_command(outputs, references, ignore_history=True))

    @attr('slow')
    def test_um_land_pp_monthly_4d_mrlsl(self):
        # ajnjg, 360_day, (lat, lon, time, sdepth).
        input_dir = self.input_dir.format('CMIP5', 'Lmon', 'mrlsl')
        outputs, references = self.convert(
            input_dir, 'data_out', 'reference_output',
            ['mrlsl_Lmon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc'])
        self.compare(
            self.compare_command(outputs, references, ignore_history=True))

    @attr('slow')
    def test_um_land_pp_monthly_4d_mrsos(self):
        # ajnjg, 360_day, (lat, lon, time, sdepth1).
        input_dir = self.input_dir.format('CMIP5', 'Lmon', 'mrsos')
        outputs, references = self.convert(
            input_dir, 'data_out', 'reference_output',
            ['mrsos_Lmon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc'])
        self.compare(
            self.compare_command(outputs, references, ignore_history=True))

    @attr('slow')
    def test_um_land_pp_monthly_4d_tsl(self):
        # ajnjg, 360_day, (lat, lon, time, sdepth).
        input_dir = self.input_dir.format('CMIP5', 'Lmon', 'tsl')
        outputs, references = self.convert(
            input_dir, 'data_out', 'reference_output',
            ['tsl_Lmon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc'])
        self.compare(
            self.compare_command(outputs, references, ignore_history=True))

    @attr('slow')
    def test_um_atmosphere_pp_monthly_4d_clmcalipso(self):
        # u-an644, 360_day, (lat, lon, time, p560).
        input_dir = self.input_dir.format('CMIP6', 'CFmon', 'clmcalipso')
        outputs, references = self.convert(
            input_dir, 'data_out', 'reference_output',
            ['clmcalipso_CFmon_UKESM1-0-LL_amip_r1i1p1f1_gn_197904-197904.nc'])
        self.compare(
            self.compare_command(outputs, references, ignore_history=True))

    # @attr('slow')  # 276
    # def test_um_atmosphere_pp_monthly_4d_cfadDbze94(self):
    #     # u-an644, 360_day, (lat, lon, time, alt40, dbze).
    #     input_dir = self.input_dir.format('CMIP6', 'Emon', 'cfadDbze94')
    #     outputs, references = self.convert(
    #         input_dir, 'data_out', 'reference_output',
    #         ['cfadDbze94_Emon_UKESM1-0-LL_amip_r1i1p1f1_gn_'
    #          '197904-197904.nc'])
    #     self.compare(
    #         self.compare_command(outputs, references))

    @attr('slow')
    def test_um_atmosphere_pp_monthly_rotated_pole_4d_tas(self):
        # aklfg, gregorian, (lat, lon, time, height2m).
        input_dir = self.input_dir.format('CMIP5', 'Amon', 'tas_rotated_pole')
        outputs, references = self.convert(
            input_dir, 'data_out', 'reference_output',
            ['tas_Amon_HadGEM2-ES_rcp85_r1i1p1f1_198901-198901.nc'])
        # Ignoring the calendar attribute can be removed once #730 is
        # resolved.
        self.compare(
            self.compare_command(outputs, references, tolerance_value='7e-5',
                                 ignore_history=True,
                                 other_options='--Attribute=calendar'))

    @attr('slow')
    def test_um_atmosphere_pp_daily_zonal_mean_zg(self):
        # ai674, 360_day, (pressure, lat).
        input_dir = self.input_dir.format('CMIP6', 'EdayZ', 'zg')
        outputs, references = self.convert(
            input_dir, 'data_out', 'reference_output',
            ['zg_EdayZ_HadGEM3-GC31-LL_highres-future_r1i1p1f1_gn_'
             '19500101-19500130.nc'])
        self.compare(
            self.compare_command(outputs, references, ignore_history=True))

    @attr('slow')
    def test_um_atmosphere_pp_daily_zonal_mean_vtem_fix_lbproc(self):
        # ai674, 360_day, (pressure, lat).
        input_dir = self.input_dir.format('CMIP6', 'EdayZ', 'vtem')
        outputs, references = self.convert(
            input_dir, 'data_out', 'reference_output',
            ['vtem_EdayZ_HadGEM3-GC31-LL_highres-future_r1i1p1f1_gn_'
             '19500101-19500130.nc'])
        self.compare(
            self.compare_command(outputs, references, ignore_history=True))

    @attr('slow')
    def test_um_atmosphere_pp_daily_4d_tasmin(self):
        # ajnjg, 360_day, (lat, lon, time, height2m).
        input_dir = self.input_dir.format('CMIP5', 'day', 'tasmin')
        outputs, references = self.convert(
            input_dir, 'data_out', 'reference_output',
            ['tasmin_day_HadGEM2-ES_rcp45_r1i1p1f1_20210101-20210130.nc'])
        self.compare(
            self.compare_command(outputs, references, ignore_history=True))

    @attr('slow')
    def test_um_atmosphere_pp_daily_4d_ua850(self):
        # ak991, 360_day, (lat, lon, time, p850).
        input_dir = self.input_dir.format('HELIX', 'day', 'ua850')
        outputs, references = self.convert(
            input_dir, 'data_out', 'reference_output',
            ['ua850_day_HadGEM3_swl2_r1i1p1f1_20100601-20100630.nc'])
        self.compare(
            self.compare_command(outputs, references, ignore_history=True))

    @attr('slow')
    def test_um_atmosphere_pp_6_hourly_4d_ua(self):
        # ajnjg, 360_day, (lat, lon, time, hybrid_height).
        input_dir = self.input_dir.format('CMIP5', '6hrLev', 'ua')
        output, reference = self.convert(
            input_dir, 'data_out', 'reference_output',
            ['ua_6hrLev_HadGEM2-ES_rcp45_r1i1p1f1_'
             '202101010600-202101110000.nc'])
        self.compare(
            self.compare_command(output, reference, ignore_history=True))

    @attr('slow')
    def test_um_atmosphere_pp_6_hourly_pressure_levels_4d_ua(self):
        # ajnjg, 360_day, (lat, lon, time, plev3).
        input_dir = self.input_dir.format('CMIP5', '6hrPlev', 'ua')
        outputs, references = self.convert(
            input_dir, 'data_out', 'reference_output',
            ['ua_6hrPlev_HadGEM2-ES_rcp45_r1i1p1f1_'
             '202101010600-202102010000.nc'])
        self.compare(
            self.compare_command(outputs, references, ignore_history=True))

    @attr('slow')
    def test_um_atmosphere_pp_3_hourly_4d_tas(self):
        # ajnjg, 360_day, (lat, lon, time, height2m).
        input_dir = self.input_dir.format('CMIP5', '3hr', 'tas')
        outputs, references = self.convert(
            input_dir, 'data_out', 'reference_output',
            ['tas_3hr_HadGEM2-ES_rcp45_r1i1p1f1_202101010300-202102010000.nc'])
        self.compare(
            self.compare_command(outputs, references, ignore_history=True))

    @attr('slow')
    def test_um_atmosphere_pp_3_hourly_3d_clt(self):
        # ajnjg, 360_day, (lat, lon, time).
        input_dir = self.input_dir.format('CMIP5', '3hr', 'clt')
        outputs, references = self.convert(
            input_dir, 'data_out', 'reference_output',
            ['clt_3hr_HadGEM2-ES_rcp45_r1i1p1f1_202101010130-202101302230.nc'])
        self.compare(
            self.compare_command(outputs, references, ignore_history=True))

    @attr('slow')
    def test_nemo_netcdf_3d_tos(self):
        # no run_id, noleap, (lat, lon, time).
        input_dir = self.input_dir.format('CMIP6', 'Omon', 'tos')
        outputs, references = self.convert(
            input_dir, 'data_out', 'reference_output',
            ['tos_Omon_UKESM1-0-LL_amip_r1i1p1f1_197601-197601.nc'])
        self.compare(
            self.compare_command(outputs, references, ignore_history=True))

    @attr('slow')
    def test_nemo_netcdf_4d_thetao(self):
        # no run_id, noleap, (lat, lon, time, depth).
        input_dir = self.input_dir.format('CMIP6', 'Omon', 'thetao')
        outputs, references = self.convert(
            input_dir, 'data_out', 'reference_output',
            ['thetao_Omon_UKESM1-0-LL_amip_r1i1p1f1_197601-197601.nc'])
        self.compare(
            self.compare_command(outputs, references, ignore_history=True))

    @attr('slow')
    def test_nemo_netcdf_4d_thkcello(self):
        # no run_id, noleap, (lat, lon, time, verticle T level).
        input_dir = self.input_dir.format('CMIP6', 'Omon', 'thkcello')
        outputs, references = self.convert(
            input_dir, 'data_out', 'reference_output',
            ['thkcello_Omon_UKESM1-0-LL_amip_r1i1p1f1_197601-197601.nc'])
        self.compare(
            self.compare_command(outputs, references, ignore_history=True))

    # @attr('slow')  #129
    # def test_cice_netcdf_3d_snd(self):
    #     # no run_id, noleap, (lat, lon, time).
    #     input_dir = self.input_dir.format('CMIP6', 'SImon', 'sisnthick')
    #     outputs, references = self.convert(
    #         input_dir, 'data_out', 'reference_output',
    #         ['sisnthick_SImon_UKESM_amip_r1i1p1f1_197601-197601.nc'])
    #     self.compare(
    #         self.compare_command(outputs, references, ignore_history=True))

    @attr('slow')
    def test_cice_netcdf_3d_sndmassmelt(self):
        # ae204, inm, 360_day, (lat, lon, time).
        input_dir = self.input_dir.format('CMIP6', 'SImon', 'sndmassmelt')
        output, reference = self.convert(
            input_dir, 'data_out', 'reference_output',
            ['sndmassmelt_SImon_UKESM1-0-LL_amip_r1i1p1f1_197810-197811.nc'])
        self.compare(
            self.compare_command(output, reference, ignore_history=True))

    @attr('slow')
    def test_cice_netcdf_4d_siitdsnthick(self):
        # ae204, inm, 360_day, (lat, lon, time, iceband).
        input_dir = self.input_dir.format('CMIP6', 'SImon', 'siitdsnthick')
        output, reference = self.convert(
            input_dir, 'data_out', 'reference_output',
            ['siitdsnthick_SImon_UKESM1-0-LL_amip_r1i1p1f1_197812-197812.nc'])
        self.compare(
            self.compare_command(output, reference, ignore_history=True))

    @attr('slow')
    def test_cice_pp_3d_sifllwutop(self):
        # ae204, apm, 360_day, (lat, lon, time).
        input_dir = self.input_dir.format('CMIP6', 'SImon', 'sifllwutop')
        output, reference = self.convert(
            input_dir, 'data_out', 'reference_output',
            ['sifllwutop_SImon_UKESM1-0-LL_amip_r1i1p1f1_197812-197901.nc'])
        self.compare(
            self.compare_command(output, reference, ignore_history=True))

    @attr('slow')
    def test_cice_netcdf_daily_multiple_3d_with_different_grids(self):
        # al114, ind, 360_day, (lat, lon, time).
        input_dir = self.input_dir.format('CMIP6', 'SIday', 'multiple_3d')
        output, reference = self.convert(
            input_dir, 'data_out', 'reference_output',
            ['sisnthick_SIday_UKESM1-0-LL_amip_r1i1p1f1_gn_19781001-'
             '19781130.nc', 'sispeed_SIday_UKESM1-0-LL_amip_r1i1p1f1_gn_'
             '19781001-19781130.nc'])
        self.compare(
            self.compare_command(output, reference, ignore_history=True))

    @attr('slow')
    def test_um_atmosphere_pp_monthly_multiple_3d_variables(self):
        # ajnjg, 360_day, (lat, lon, time).
        input_dir = self.input_dir.format('CMIP5', 'Amon', 'multiple_3d')
        outputs, references = self.convert(
            input_dir, 'data_out', 'reference_output',
            ['clt_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'evspsbl_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'hfls_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'hfss_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'pr_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'prc_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'prsn_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'prw_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'ps_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'psl_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'rlds_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'rldscs_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'rlus_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'rlut_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'rlutcs_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'rsds_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'rsdscs_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'rsdt_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'rsus_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'rsuscs_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'rsut_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'rsutcs_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'sbl_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'sci_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'tauu_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'tauv_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'ts_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc'])
        self.compare(
            self.compare_command(outputs, references, ignore_history=True))

    @attr('slow')
    def test_um_atmosphere_pp_monthly_multiple_4d_variables(self):
        # ajnjg, 360_day, (lat, lon, time, height2m/10m).
        input_dir = self.input_dir.format('CMIP5', 'Amon', 'multiple_4d')
        outputs, references = self.convert(
            input_dir, 'data_out', 'reference_output',
            ['hurs_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'huss_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'sfcWind_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'tas_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'uas_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'vas_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc'])
        self.compare(
            self.compare_command(outputs, references, ignore_history=True))

    @attr('slow')
    def test_um_atmosphere_pp_monthly_multiple_hybrid_height_4d_variables(
            self):
        # ajnjg, 360_day, (lat, lon, time, hybrid_height).
        input_dir = self.input_dir.format('CMIP5', 'Amon',
                                          'multiple_hybrid_height')
        outputs, references = self.convert(
            input_dir, 'data_out', 'reference_output',
            ['cl_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'cli_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'clw_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc'])
        self.compare(
            self.compare_command(outputs, references, ignore_history=True))

    @attr('slow')
    def test_um_atmosphere_pp_monthly_multiple_pressure_level_4d_variables(
            self):
        # ajnjg, 360_day, (lat, lon, time, plevs).
        input_dir = self.input_dir.format('CMIP5', 'Amon',
                                          'multiple_pressure_level')
        outputs, references = self.convert(
            input_dir, 'data_out', 'reference_output',
            ['hur_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'hus_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'ta_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'ua_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'va_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'wap_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc',
             'zg_Amon_HadGEM2-ES_rcp45_r1i1p1f1_202101-202101.nc'])
        self.compare(
            self.compare_command(outputs, references, ignore_history=True))


class TestGetModelToMIPMappings(unittest.TestCase):
    """
    Tests for ``get_model_to_mip_mappings`` in request.py.
    """

    def setUp(self):
        """
        Create the |model to MIP mappings| configuration file.
        """
        self.dirname = os.path.join(
            os.path.dirname(os.path.realpath(request.__file__)), 'process')
        variable_name = 'tas'
        constraint = 'stash'
        expression = 'constraint'
        positive = 'up'
        stash = 'm01s03i236'
        units = 'K'
        self.model_to_mip_mapping_config = (
            '[{variable_name}]\n'
            'constraint = {constraint}\n'
            'expression = {expression}\n'
            'positive = {positive}\n'
            'stash = {stash}\n'
            'units = {units}\n'.format(
                variable_name=variable_name, constraint=constraint,
                expression=expression, positive=positive, stash=stash,
                units=units))

    @patch('__builtin__.open')
    def test_common_model_to_mip_mappings(self, mopen):
        model_configuration = 'HadCM'
        mip_table_name = 'CMIP6_Lmon'
        pathnames = [os.path.join(self.dirname, 'common_mappings.cfg')]
        self._obj_instantiation(mopen, model_configuration, mip_table_name,
                                pathnames)

    @patch('__builtin__.open')
    def test_common_mip_table_id_model_to_mip_mappings(self, mopen):
        model_configuration = 'HadCM'
        mip_table_id = 'Amon'
        mip_table_name = 'CMIP6_Amon'
        filenames = [
            'common_mappings.cfg',
            '{mip_table_id}_mappings.cfg'.format(mip_table_id=mip_table_id)]
        pathnames = [
            os.path.join(self.dirname, filename) for filename in filenames]
        self._obj_instantiation(mopen, model_configuration, mip_table_name,
                                pathnames)

    @patch('__builtin__.open')
    def test_common_model_configuration_mip_table_id_model_to_mip_mappings(
            self, mopen):
        model_configuration = 'HadGEM2-ES'
        base_model_configuration = model_configuration.split('-')[0]
        mip_table_id = 'Amon'
        mip_table_name = 'CMIP6_Amon'
        filenames = [
            'common_mappings.cfg',
            '{base_model_configuration}_mappings.cfg'.format(
                base_model_configuration=base_model_configuration),
            '{mip_table_id}_mappings.cfg'.format(mip_table_id=mip_table_id),
            '{base_model_configuration}_{mip_table_id}_mappings.cfg'.format(
                base_model_configuration=base_model_configuration,
                mip_table_id=mip_table_id)]
        pathnames = [
            os.path.join(self.dirname, filename) for filename in filenames]
        self._obj_instantiation(mopen, model_configuration, mip_table_name,
                                pathnames)

    def _obj_instantiation(self, mopen, model_configuration, mip_table_name,
                           pathnames):
        mopen.return_value = BytesIO(dedent(self.model_to_mip_mapping_config))
        get_model_to_mip_mappings(model_configuration, mip_table_name)
        call_args_list = [call(pathname) for pathname in pathnames]
        self.assertEqual(mopen.call_args_list, call_args_list)


class TestGetMIPTable(unittest.TestCase):
    """
    Tests for ``get_mip_table`` in request.py.
    """

    def setUp(self):
        self.mip_table_dir = 'mip_table_dir'
        self.mip_table_name = 'mip_table_name.json'
        self.mip_table = (
            '{"Header": {"table_id": "Table Amon", "realm": "atmos"}}')

    @patch('__builtin__.open')
    def test_is_instance_mip_config(self, mopen):
        mopen.return_value = BytesIO(dedent(self.mip_table))
        obj = get_mip_table(self.mip_table_dir, self.mip_table_name)
        mip_table_path = os.path.join(self.mip_table_dir, self.mip_table_name)
        mopen.assert_called_once_with(mip_table_path)
        self.assertIsInstance(obj, cfg.MIPConfig)


class TestGetVariableModelToMIPMappings(unittest.TestCase):
    """
    Tests for ``get_variable_model_to_mip_mappings`` in request.py.
    """

    def setUp(self):
        """
        Create the :class:`configuration.ModelToMIPMappingConfig` object.
        """
        self.model = 'HadGEM3'
        self.mip_table_id = 'Amon'
        self.mip_table_name = 'CMIP6_{}'.format(self.mip_table_id)
        self.variable_name = 'grassFrac'
        self.model_to_mip_mapping = {
            'expression': '(m01s19i013[lbplev=3] + m01s19i013[lbplev = 4] '
                          '- m01s19i012) * m01s00i505',
            'positive': 'None', 'units': '1', 'valid_min': '0.0'}

    @staticmethod
    @patch('__builtin__.open')
    def _model_to_mip_mappings(variable_name, model_to_mip_mapping, model,
                               mip_table_name, mopen):
        model_to_mip_mapping_string = ''.join(
            ['{option} = {value}\n'.format(option=option, value=value) for
             option, value in model_to_mip_mapping.iteritems()])
        model_to_mip_mapping_config = (
            '[{variable_name}]\n'
            '{model_to_mip_mapping_string}'.format(
                variable_name=variable_name,
                model_to_mip_mapping_string=model_to_mip_mapping_string))
        mopen.return_value = BytesIO(dedent(model_to_mip_mapping_config))
        return get_model_to_mip_mappings(model, mip_table_name)

    def test_variable_model_to_mip_mapping(self):
        reference = {}
        reference.update(self.model_to_mip_mapping)
        updated_model_to_mip_mapping = {
            'constraint1': 'stash1, lbplev1', 'constraint2': 'stash2, lbplev2',
            'constraint3': 'stash3', 'constraint4': 'stash4', 'expression':
                '(constraint1 + constraint2 - constraint3) * constraint4',
            'lbplev1': '3', 'lbplev2': '4', 'stash1': 'm01s19i013',
            'stash2': 'm01s19i013', 'stash3': 'm01s19i012',
            'stash4': 'm01s00i505'}
        reference.update(updated_model_to_mip_mapping)
        model_to_mip_mapping_obj = self._model_to_mip_mappings(
            self.variable_name, self.model_to_mip_mapping, self.model,
            self.mip_table_name)
        obj = get_variable_model_to_mip_mapping(
            model_to_mip_mapping_obj, self.variable_name, self.mip_table_name,
            None)
        self._assert_dict_equal(obj.model_to_mip_mapping, reference)

    def test_variable_name_with_numerical_suffix_already_in_mappings(self):
        variable_name = 'wap500'
        model_to_mip_mapping = {
            'expression': 'm01s30i208[lbproc=128, blev=500.0] '
                          '/ m01s30i301[lbproc=128, blev=500.0]',
            'positive': 'None', 'units': 'Pa s-1'}
        model_to_mip_mapping_obj = self._model_to_mip_mappings(
            variable_name, model_to_mip_mapping, self.model,
            self.mip_table_name)
        obj = get_variable_model_to_mip_mapping(
            model_to_mip_mapping_obj, variable_name, self.mip_table_name, None)
        reference = {
            'blev1': '500.0', 'blev2': '500.0', 'positive': 'None',
            'units': 'Pa s-1', 'stash2': 'm01s30i301', 'stash1': 'm01s30i208',
            'lbproc1': '128', 'lbproc2': '128',
            'expression': 'constraint1 / constraint2',
            'constraint1': 'stash1, lbproc1, blev1',
            'constraint2': 'stash2, lbproc2, blev2'}
        self._assert_dict_equal(obj.model_to_mip_mapping, reference)

    def test_expression_contains_timestep(self):
        mip_table_name = 'CMIP6_CFmon'
        variable_name = 'tnt'
        model_to_mip_mapping = {
            'expression': 'm01s30i181[lbproc=128] / ATMOS_TIMESTEP',
            'positive': 'None', 'units': 'K s-1'}
        atmos_timestep = 600
        reference = {}
        reference.update(model_to_mip_mapping)
        updated_model_to_mip_mapping = {
            'constraint1': 'stash1, lbproc1',
            'expression': 'constraint1 / {}'.format(atmos_timestep),
            'lbproc1': '128', 'stash1': 'm01s30i181'}
        reference.update(updated_model_to_mip_mapping)
        model_to_mip_mapping_obj = self._model_to_mip_mappings(
            variable_name, model_to_mip_mapping, self.model, mip_table_name)
        obj = get_variable_model_to_mip_mapping(
            model_to_mip_mapping_obj, variable_name, mip_table_name,
            atmos_timestep)
        self._assert_dict_equal(obj.model_to_mip_mapping, reference)

    def test_expression_contains_timestep_but_no_value_provided(self):
        mip_table_name = 'CMIP6_CFmon'
        variable_name = 'tnt'
        model_to_mip_mapping = {
            'expression': 'm01s30i181[lbproc=128] / ATMOS_TIMESTEP',
            'positive': 'None', 'units': 'K s-1'}
        model_to_mip_mapping_obj = self._model_to_mip_mappings(
            variable_name, model_to_mip_mapping, self.model, mip_table_name)
        msg = ('The model to MIP mapping expression contains the atmospheric '
               'model timestep but no value was defined in the user '
               'configuration file')
        self.assertRaisesRegexp(
            RuntimeError, msg, get_variable_model_to_mip_mapping,
            model_to_mip_mapping_obj, variable_name, mip_table_name, None)

    def test_missing_expression(self):
        # See, e.g. sbl in common_mappings.cfg
        variable_name = 'sbl'
        model_to_mip_mapping = {'units': 'kg m-2 s-1'}
        mip_table_name = 'CMIP6_CFsubhr'
        model_to_mip_mapping_obj = self._model_to_mip_mappings(
            variable_name, model_to_mip_mapping, self.model, mip_table_name)
        msg = 'No expression available for'
        self.assertRaisesRegexp(
            RuntimeError, msg, get_variable_model_to_mip_mapping,
            model_to_mip_mapping_obj, variable_name, mip_table_name, None)

    def _assert_dict_equal(self, output_dict, reference_dict):
        self.assertEqual(len(output_dict), len(reference_dict))
        for output_key, output_value in output_dict.iteritems():
            self.assertIn(output_key, reference_dict)
            self.assertEqual(output_value, reference_dict[output_key])


class TestGetRequestedVariables(unittest.TestCase):
    """
    Tests for ``get_requested_variables`` in request.py.
    """

    def setUp(self):
        """
        Create the requested variables.
        """
        self.stream_id_1 = 'apa'
        mip_table_name_1 = 'CMIP5_daily'
        var_1 = 'tas'
        var_2 = 'pr'
        self.stream_id_2 = 'apm'
        mip_table_name_2 = 'CMIP5_Amon'
        var_3 = 'ua'
        self.requested_variables = {
            (self.stream_id_1, mip_table_name_1): [var_1, var_2],
            (self.stream_id_1, mip_table_name_2): [var_2],
            (self.stream_id_2, mip_table_name_2): [var_1, var_3]}
        self.user_config = DummyUserConfig(self.requested_variables)

    def test_requested_stream_ids_is_none(self):
        requested_variables = get_requested_variables(self.user_config, None)
        reference = self.requested_variables
        self.assertEquals(requested_variables, reference)

    def test_request_single_stream_id(self):
        requested_variables = get_requested_variables(self.user_config,
                                                      self.stream_id_1)
        reference = {key: value for key, value in
                     self.requested_variables.iteritems() if
                     self.stream_id_1 in key}
        self.assertEquals(requested_variables, reference)


class DummyUserConfig(object):
    def __init__(self, requested_variables):
        self.streams_to_process = requested_variables


if __name__ == '__main__':
    unittest.main()
