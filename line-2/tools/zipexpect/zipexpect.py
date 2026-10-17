#!/usr/bin/env python3
"""Require independently expected file paths, lengths and SHA-256 before extraction."""
import argparse
import json
import math
from pathlib import Path
import re
import sys
import time
import zipfile
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'zipgate'))
from zipgate import Rejected, local_path, positive, process as gate_process
from safezip import member_name


def policy_files(policy, entries=1000):
    """Validate a small, explicit schema, including normalized implicit parents."""
    positive('entries', entries)
    if not isinstance(policy, dict) or set(policy) != {'files'}:
        raise Rejected('policy must have exactly the files key')
    files = policy['files']
    if not isinstance(files, list) or len(files) > entries:
        raise Rejected('files must be a list within entry limit')
    expected, nodes = {}, {}
    for record in files:
        if not isinstance(record, dict) or set(record) != {'path', 'bytes', 'sha256'}:
            raise Rejected('each expected file requires exactly path, bytes, sha256')
        name, size, digest = record['path'], record['bytes'], record['sha256']
        if not isinstance(name, str) or not name or name.endswith('/'):
            raise Rejected('expected path must name a file')
        # Reuse the extraction policy rather than accepting a second path syntax.
        info = zipfile.ZipInfo(name)
        if member_name(info) != name:
            raise Rejected('expected path is not canonical')
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise Rejected('expected bytes must be a nonnegative integer')
        if not isinstance(digest, str) or not re.fullmatch('[0-9a-fA-F]{64}', digest):
            raise Rejected('expected SHA-256 must be 64 hex characters')
        if name in expected:
            raise Rejected('duplicate expected file')
        parts = name.split('/')
        for index in range(1, len(parts) + 1):
            path = '/'.join(parts[:index])
            node = (path, index < len(parts))
            old = nodes.get(path.casefold())
            if old is not None and old != node:
                raise Rejected('expected file/directory or case collision')
            nodes[path.casefold()] = node
        expected[name] = {'bytes': size, 'sha256': digest.lower()}
    return expected, {path for path, directory in nodes.values() if directory}


def load_policy(path, *, policy_bytes=1048576):
    positive('policy_bytes', policy_bytes)
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise Rejected('duplicate JSON key in policy')
            result[key] = value
        return result
    with local_path(path).open('rb') as reader:
        data = reader.read(policy_bytes + 1)
    if len(data) > policy_bytes:
        raise Rejected('policy byte limit exceeded')
    try:
        return json.loads(data, object_pairs_hook=unique)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise Rejected('invalid policy JSON') from error


def process(archive_path, policy, output=None, *, seconds=None, cancelled=None,
            **limits):
    """Inspect all archive payloads; publish only after exact expected-tree match.

    Policies must come from an independent trusted source to add authenticity.
    No archive member is executed. Resource controls are inherited from ZipGate.
    """
    if seconds is not None:
        try:
            valid = (not isinstance(seconds, bool) and isinstance(seconds, (int, float))
                     and math.isfinite(seconds) and seconds > 0)
        except OverflowError:
            valid = False
        if not valid:
            raise Rejected('seconds must be finite and positive')
    if cancelled is not None and not callable(cancelled):
        raise Rejected('cancelled must be callable')
    started = time.monotonic()
    def checkpoint():
        if cancelled is not None and cancelled():
            raise Rejected('operation cancelled')
        if seconds is not None and time.monotonic() - started >= seconds:
            raise Rejected('operation time budget exceeded')
        return False
    checkpoint()
    expected, parents = policy_files(policy, limits.get('entries', 1000))
    checkpoint()
    checked = gate_process(archive_path, cancelled=checkpoint, **limits)
    actual = {}
    for entry in checked['entries']:
        checkpoint()
        name = entry['path']
        if entry['kind'] == 'directory':
            if name not in parents:
                raise Rejected('unexpected directory: ' + repr(name))
        else:
            actual[name] = {'bytes': entry['bytes'], 'sha256': entry['sha256']}
    if set(actual) != set(expected):
        raise Rejected('expected file paths differ from archive')
    for name in sorted(expected):
        checkpoint()
        if actual[name] != expected[name]:
            raise Rejected('expected file content differs: ' + repr(name))
    checkpoint()
    if output is not None:
        # Gate's own fresh snapshot must match reviewed bytes before parsing or
        # staging; pathname replacement cannot introduce an unchecked package.
        extraction_limits = dict(limits, expected_sha256=checked['archive_sha256'])
        checked = gate_process(archive_path, output, cancelled=checkpoint,
                               **extraction_limits)
    return {'ok': True, 'mode': 'extract' if output is not None else 'inspect',
            'archive_sha256': checked['archive_sha256'],
            'expected_files': len(expected), 'expected_content_matched': True,
            'total_bytes': checked['total_bytes'], 'preflight': checked['preflight']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('inspect', 'extract'))
    parser.add_argument('archive')
    parser.add_argument('policy')
    parser.add_argument('output', nargs='?')
    parser.add_argument('--policy-bytes', type=int, default=1048576)
    parser.add_argument('--seconds', type=float)
    parser.add_argument('--sha256', dest='expected_sha256')
    for name, default in [('entries', 1000), ('directory-bytes', 2097152),
                          ('archive-bytes', 33554432), ('nodes', 32000),
                          ('file-bytes', 16777216), ('total-bytes', 67108864), ('ratio', 200)]:
        parser.add_argument('--' + name, type=int, default=default)
    args = vars(parser.parse_args())
    command = args.pop('command')
    if (command == 'extract') != (args['output'] is not None):
        parser.error('extract requires output; inspect takes no output')
    try:
        policy = load_policy(args.pop('policy'), policy_bytes=args.pop('policy_bytes'))
        args['archive_path'] = args.pop('archive')
        report = process(policy=policy, **args)
    except (ValueError, OSError, zipfile.BadZipFile, NotImplementedError,
            RuntimeError, EOFError, zlib.error) as error:
        print(json.dumps({'ok': False, 'error': str(error)}, ensure_ascii=True))
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
