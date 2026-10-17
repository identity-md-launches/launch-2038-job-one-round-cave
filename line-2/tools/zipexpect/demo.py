#!/usr/bin/env python3
"""Replay the shipped historical public IMD capture, without network access."""
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile
from zipexpect import Rejected, local_path, process


def main():
    capture = local_path(Path(__file__).resolve().parents[1] / 'safezip/imd-openapi.json')
    with capture.open('rb') as reader:
        payload = reader.read(65537)
    digest = 'be142840c010710cb2a5b9e5c73e71d8e79ec4054c15661699d60bfa627be96a'
    assert hashlib.sha256(payload).hexdigest() == digest
    policy = {'files': [{'path': 'docs/openapi.json', 'bytes': 23132, 'sha256': digest}]}
    scratch = local_path('test/scratch')
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch, prefix='zipexpect-demo-') as temporary:
        root = Path(temporary)
        source, output = root / 'input.zip', root / 'unpacked'
        def pack(extra=False):
            with zipfile.ZipFile(source, 'w', zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('docs/openapi.json', payload)
                if extra:
                    archive.writestr('unexpected.py', b'print("not executed")')
        pack(True)
        try:
            process(source, policy, output)
        except Rejected as error:
            refusal = str(error)
            assert not output.exists()
        else:
            raise AssertionError('unexpected file accepted')
        pack()
        report = process(source, policy, output, seconds=10)
        assert (output / 'docs/openapi.json').read_bytes() == payload
        print(json.dumps({'ok': True, 'network_used': False,
                          'source': 'https://api.imd.fun/openapi.json',
                          'historical_capture': True, 'extra_file_refused': refusal,
                          'extracted_bytes_identical': True, 'report': report}, indent=2))


if __name__ == '__main__':
    main()
