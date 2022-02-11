import shutil
import json, yaml
import os
import re
import time

from pathlib import Path

import pytest

import ase.io

from wfl.configset import ConfigSet_in
from wfl.fit.ace import fit, prepare_params_and_fit

have_julia_with_modules = os.system("julia -e  'using ACE1pack'") == 0

@pytest.mark.skipif(not have_julia_with_modules, reason="no julia with appropriate modules available")
def test_ace_fit_dry_run(request, tmp_path, monkeypatch, run_dir='run_dir'):

    print('getting fitting data from ', request.fspath)

    # kinda ugly, but remote running of multistage fit doesn't support absolute run_dir, so test
    # with a relative one
    monkeypatch.chdir(tmp_path)
    (tmp_path / run_dir).mkdir()

    fit_config_file = os.path.join(os.path.dirname(request.fspath), 'assets', 'B_DFT_data.xyz')

    # Only mandatory params
    params = {
        "data": {},
        "basis": {
            "rpi": {"type": "rpi", "species": ["B"], "N": 3, "maxdeg": 6},
            "pair": {"type": "pair", "species": ["B"], "maxdeg": 4}},
        "solver": {"solver": "lsqr"}}

    t0 = time.time()
    ACE_size = prepare_params_and_fit(
        ConfigSet_in(input_files=fit_config_file),
        ACE_fname_stem='ACE.B_test', 
        ace_fit_params=params, 
        ref_property_prefix='REF_',
        run_dir=str(run_dir), 
        dry_run=True, 
        skip_if_present=True)
    time_actual = time.time() - t0

    assert len(ACE_size) == 2
    assert isinstance(ACE_size[0], int) and isinstance(ACE_size[1], int)

    assert os.path.exists(os.path.join(tmp_path, run_dir, f'ACE.B_test.size'))

    t0 = time.time()
    ACE_size_rerun = prepare_params_and_fit(
        ConfigSet_in(input_files=fit_config_file),
        ACE_fname_stem='ACE.B_test', 
        ace_fit_params=params, 
        ref_property_prefix='REF_',
        run_dir=str(run_dir), 
        dry_run=True, 
        skip_if_present=True)
    time_rerun = time.time() - t0

    assert ACE_size == ACE_size_rerun

    # rerun should reuse files, be much faster
    assert time_rerun < time_actual / 10


@pytest.mark.skipif(not have_julia_with_modules, reason="no julia with appropriate modules available")
def test_ace_fit(request, tmp_path, monkeypatch, run_dir='run_dir'):
    print('getting fitting data from ', request.fspath)

    # kinda ugly, but remote running of multistage fit doesn't support absolute run_dir, so test
    # with a relative one
    monkeypatch.chdir(tmp_path)
    (tmp_path / run_dir).mkdir()

    fit_config_file = os.path.join(os.path.dirname(request.fspath), 'assets', 'B_DFT_data.xyz')
    # Only mandatory params
    params = {
        "data": {},
        "basis": {
            "rpi": {"type": "rpi", "species": ["B"], "N": 3, "maxdeg": 6},
            "pair": {"type": "pair", "species": ["B"], "maxdeg": 4}},
        "solver": {"solver": "lsqr"}}

    # removed from fit, maybe should do here, if we actually want to test the resulting potential?
    # database_modify_mod='wfl.fit.modify_database.gap_rss_set_config_sigmas_from_convex_hull',

    t0 = time.time()
    ACE = prepare_params_and_fit(
        ConfigSet_in(input_files=fit_config_file),
        ACE_fname_stem='ACE.B_test', 
        ace_fit_params=params, 
        ref_property_prefix='REF_',
        run_dir=str(run_dir), 
        skip_if_present=True)
    time_actual = time.time() - t0
    print('ACE', ACE)

    assert os.path.exists(os.path.join(tmp_path, run_dir, f'ACE.B_test.json'))
    # assert os.path.exists(os.path.join(tmp_path, run_dir, f'ACE.B_test.yace'))

    t0 = time.time()
    ACE = prepare_params_and_fit(
        ConfigSet_in(input_files=fit_config_file),
        ACE_fname_stem='ACE.B_test', 
        ace_fit_params=params, 
        ref_property_prefix='REF_',
        run_dir=str(run_dir), 
        skip_if_present=True)
    time_rerun = time.time() - t0

    # rerun should reuse files, be much faster
    assert time_rerun < time_actual / 10


@pytest.mark.skipif(not have_julia_with_modules, reason="no julia with appropriate modules available")
@pytest.mark.remote
def test_ace_fit_remote(request, tmp_path, expyre_systems, monkeypatch):
    ri = {'resources' : {'max_time': '10m', 'n': [1, 'nodes']},
          'pre_cmds': [ f'export PYTHONPATH={Path(__file__).parent.parent}:$PYTHONPATH'],
          'env_vars' : ['ACE_FIT_JULIA_THREADS=$( [ $EXPYRE_NCORES_PER_NODE -gt 2 ] && echo 2 || echo $(( $EXPYRE_NCORES_PER_NODE )) )', 'ACE_FIT_BLAS_THREADS=$EXPYRE_NCORES_PER_NODE' ]}

    for sys_name in expyre_systems:
        if sys_name.startswith('_'):
            continue

        ri['sys_name'] = sys_name
        ri['job_name'] = 'pytest_ace_fit_'+sys_name

        if 'WFL_PYTEST_REMOTEINFO' in os.environ:
            ri_extra = json.loads(os.environ['WFL_PYTEST_REMOTEINFO'])
            if 'resources' in ri_extra:
                ri['resources'].update(ri_extra['resources'])
                del ri_extra['resources']
            ri.update(ri_extra)

        monkeypatch.setenv('WFL_ACE_FIT_REMOTEINFO', json.dumps(ri))
        test_ace_fit(request, tmp_path, monkeypatch, run_dir=f'run_dir_{sys_name}')