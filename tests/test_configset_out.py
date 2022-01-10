import time
from pathlib import Path

from ase.atoms import Atoms

from wfl.configset import ConfigSet_out


def test_configset_out_flush_interval(tmpdir):
    outfile = str(Path(tmpdir) / 'co.0.xyz')
    co = ConfigSet_out(output_files=outfile, all_or_none=False)
    co.pre_write()

    for i in range(10):
        at = Atoms('H')
        co.write(at, flush_interval=5)
        if i < 5:
            # first 5 should be fast, no flush, size should be 0
            assert Path(outfile).stat().st_size == 0
        elif i == 5:
            # wait past interval
            time.sleep(6)
        else:
            # after flush interval size should be > 0
            assert Path(outfile).stat().st_size > 0

    co.end_write()

    assert Path(outfile).stat().st_size > 0


def test_configset_out_flush_always(tmpdir):
    outfile = str(Path(tmpdir) / 'co.1.xyz')
    co = ConfigSet_out(output_files=outfile, all_or_none=False)
    co.pre_write()

    for i in range(10):
        at = Atoms('H')
        co.write(at, flush_interval=0)

        assert Path(outfile).stat().st_size > 0

    co.end_write()

    assert Path(outfile).stat().st_size > 0


def test_all_or_none(tmpdir):
    outfile = str(Path(tmpdir) / 'co.1.xyz')
    co = ConfigSet_out(output_files=outfile)
    co.pre_write()

    for i in range(10):
        at = Atoms('H')
        co.write(at, flush_interval=0)

    assert not Path(outfile).exists()

    co.end_write()

    assert Path(outfile).stat().st_size > 0
