"""Adversarial archive input and independent recovery actions; no privileged work."""
import hashlib
import importlib.util
import io
from pathlib import Path
import tarfile

import pytest

spec = importlib.util.spec_from_file_location('demo_update', Path(__file__).resolve().parents[1]/'scripts/update-demo.py')
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)
COMMIT = 'a'*40
PREFIX = 'release-'+COMMIT


def archive(extra=None):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer,mode='w',format=tarfile.PAX_FORMAT,pax_headers={'comment':COMMIT}) as target:
        for name in ('Dockerfile','docker-compose.yml','docker-compose.pilot.yml','app/__init__.py'):
            item=tarfile.TarInfo(PREFIX+'/'+name);content=b'reviewed fixture';item.size=len(content)
            target.addfile(item,io.BytesIO(content))
        if extra:
            target.addfile(extra,io.BytesIO(b'') if extra.isfile() else None)
    return buffer.getvalue()


def test_extracts_the_same_verified_bytes_if_original_path_changes(tmp_path):
    supplied=tmp_path/'upload.tar';supplied.write_bytes(archive())
    immutable=supplied.read_bytes()
    assert updater.validate_archive(immutable,hashlib.sha256(immutable).hexdigest(),COMMIT)==PREFIX
    supplied.write_bytes(b'replaced after validation')
    destination=tmp_path/'release'
    updater.extract_archive(immutable,destination)
    assert (destination/'app/__init__.py').read_bytes()==b'reviewed fixture'


@pytest.mark.parametrize('name,kind', [
    (PREFIX+'/../escape',tarfile.REGTYPE),('/tmp/escape',tarfile.REGTYPE),
    ('wrong-root/file',tarfile.REGTYPE),(PREFIX+'/link',tarfile.SYMTYPE),
    (PREFIX+'/hardlink',tarfile.LNKTYPE),(PREFIX+'/device',tarfile.CHRTYPE),
    (PREFIX+'/Dockerfile',tarfile.REGTYPE),
])
def test_rejects_unsafe_archive_members(name,kind):
    extra=tarfile.TarInfo(name);extra.type=kind
    payload=archive(extra)
    with pytest.raises(ValueError):updater.validate_archive(payload,hashlib.sha256(payload).hexdigest(),COMMIT)


def test_rejects_checksum_and_claimed_identity_mismatch():
    payload=archive()
    with pytest.raises(ValueError):updater.validate_archive(payload,'0'*64,COMMIT)
    with pytest.raises(ValueError):updater.validate_archive(payload,hashlib.sha256(payload).hexdigest(),'b'*40)


@pytest.mark.parametrize('failing', ['service','pointer','report'])
def test_reporting_and_pointer_failures_cannot_prevent_service_recovery(failing):
    called=[]
    def action(name):
        def run():
            called.append(name)
            if name==failing:raise OSError('simulated failure')
        return run
    assert updater.recover(action('service'),action('pointer'),action('report'))==[failing]
    assert called==['service','pointer','report']
