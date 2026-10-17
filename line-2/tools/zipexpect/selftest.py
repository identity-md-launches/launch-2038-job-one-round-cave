#!/usr/bin/env python3
"""Offline expected-content and publication regression tests."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import zipexpect as ze


def expected(items):
    return {'files': [{'path': n, 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}
                      for n, b in items if not n.endswith('/')]}


class ExpectTests(unittest.TestCase):
    def setUp(self):
        scratch = ze.local_path('test/scratch')
        scratch.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=scratch, prefix='zipexpect-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.archive = self.root / 'input.zip'
        self.output = self.root / 'out'
        self.items = [('docs/a', b'hello'), ('docs/b', b'world')]
        self.policy = expected(self.items)
        self.pack(self.items)

    def pack(self, items):
        with zipfile.ZipFile(self.archive, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, payload in items:
                archive.writestr(name, payload)

    def refuse(self, policy=None, **kwargs):
        with self.assertRaises(ze.Rejected):
            ze.process(self.archive, self.policy if policy is None else policy,
                       self.output, **kwargs)
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.root.glob('.safezip-*')))

    def test_inspect_no_output(self):
        report = ze.process(self.archive, self.policy)
        self.assertEqual(report['mode'], 'inspect')
        self.assertEqual(report['expected_files'], 2)
        self.assertFalse(self.output.exists())

    def test_extract_exact(self):
        report = ze.process(self.archive, self.policy, self.output)
        self.assertEqual(report['mode'], 'extract')
        self.assertEqual((self.output / 'docs/a').read_bytes(), b'hello')
        self.assertEqual((self.output / 'docs/b').read_bytes(), b'world')
        self.assertEqual(report['total_bytes'], 10)

    def test_missing_file(self):
        self.pack(self.items[:1])
        self.refuse()

    def test_extra_file(self):
        self.pack(self.items + [('extra', b'')])
        self.refuse()

    def test_unexpected_empty_directory(self):
        self.pack(self.items + [('empty/', b'')])
        self.refuse()

    def test_explicit_expected_parent(self):
        self.pack([('docs/', b'')] + self.items)
        self.assertTrue(ze.process(self.archive, self.policy, self.output)['ok'])

    def test_same_size_wrong_content(self):
        self.pack([('docs/a', b'HELLO'), self.items[1]])
        self.refuse()

    def test_wrong_size(self):
        self.policy['files'][0]['bytes'] += 1
        self.refuse()

    def test_empty_policy_and_archive(self):
        self.pack([])
        self.assertEqual(ze.process(self.archive, {'files': []}, self.output)['total_bytes'], 0)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_uppercase_hash(self):
        for record in self.policy['files']:
            record['sha256'] = record['sha256'].upper()
        self.assertTrue(ze.process(self.archive, self.policy)['ok'])

    def test_policy_shape(self):
        for policy in (None, [], {}, {'files': {}}, {'files': [], 'extra': 1},
                       {'files': [None]}, {'files': [{'path': 'a'}]}):
            with self.subTest(policy=policy), self.assertRaises(ze.Rejected):
                ze.policy_files(policy)

    def test_bad_values(self):
        for field, values in [('bytes', [True, -1, 1.5, '2']),
                              ('sha256', [None, '0'*63, 'x'*64]),
                              ('path', [None, '', '../escape', 'a/', 'a\x00b',
                                        'a\\b', 'CON', 'e\u0301'])]:
            for value in values:
                with self.subTest(field=field, value=value):
                    record = dict(self.policy['files'][0], **{field: value})
                    with self.assertRaises(ze.Rejected):
                        ze.policy_files({'files': [record]})

    def test_policy_collisions(self):
        for names in [('a', 'a'), ('A/x', 'a/y'), ('a', 'a/b'), ('a/b', 'a'),
                      ('Straße/x', 'STRASSE/y')]:
            with self.subTest(names=names), self.assertRaises(ze.Rejected):
                ze.policy_files(expected([(n, b'') for n in names]))

    def test_policy_order_irrelevant(self):
        self.policy['files'].reverse()
        self.assertTrue(ze.process(self.archive, self.policy)['ok'])

    def test_policy_entry_limit(self):
        self.refuse(entries=1)
        for value in (0, True, -1, 1.5):
            with self.assertRaises(ze.Rejected):
                ze.policy_files(self.policy, value)

    def test_archive_limits(self):
        for kwargs in ({'archive_bytes': 1}, {'directory_bytes': 1},
                       {'nodes': 1}, {'file_bytes': 4}, {'total_bytes': 9}):
            with self.subTest(kwargs=kwargs):
                self.refuse(**kwargs)

    def test_unsafe_member_not_ignored(self):
        self.pack(self.items + [('../escape', b'bad')])
        self.refuse()

    def test_archive_digest(self):
        self.refuse(expected_sha256='0'*64)
        digest = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        self.assertTrue(ze.process(self.archive, self.policy,
                                  expected_sha256=digest)['ok'])

    def test_replaced_archive_before_extraction(self):
        original = ze.gate_process
        calls = []
        def replace(*args, **kwargs):
            calls.append(True)
            if len(calls) == 2:
                self.pack([('docs/a', b'HELLO'), self.items[1]])
            return original(*args, **kwargs)
        with patch.object(ze, 'gate_process', side_effect=replace):
            self.refuse()
        self.assertEqual(len(calls), 2)

    def test_no_publication_on_policy_mismatch(self):
        original = ze.gate_process
        with patch.object(ze, 'gate_process', wraps=original) as gate:
            self.policy['files'][0]['sha256'] = '0'*64
            self.refuse()
            self.assertEqual(gate.call_count, 1)
            self.assertEqual(len(gate.call_args.args), 1)

    def test_existing_output_preserved(self):
        self.output.mkdir()
        (self.output / 'keep').write_bytes(b'original')
        with self.assertRaises(ze.Rejected):
            ze.process(self.archive, self.policy, self.output)
        self.assertEqual((self.output / 'keep').read_bytes(), b'original')

    def test_interruption(self):
        self.refuse(cancelled=lambda: True)
        with patch.object(ze.time, 'monotonic', side_effect=[0, 2]):
            self.refuse(seconds=1)
        for value in (0, True, float('nan'), float('inf'), 10**1000):
            self.refuse(seconds=value)
        self.refuse(cancelled=False)

    def test_policy_loader(self):
        path = self.root / 'policy.json'
        path.write_text(json.dumps(self.policy), encoding='utf-8')
        self.assertEqual(ze.load_policy(path), self.policy)
        with self.assertRaises(ze.Rejected):
            ze.load_policy(path, policy_bytes=1)
        for data in (b'{"files":[],"files":[]}', b'\xff', b'{', b'['*2000):
            path.write_bytes(data)
            with self.assertRaises(ze.Rejected):
                ze.load_policy(path)

    def test_cli(self):
        path = self.root / 'policy.json'
        path.write_text(json.dumps(self.policy))
        base = [sys.executable, '-B', ze.__file__]
        for command, tail in [('inspect', []), ('extract', [str(self.output)])]:
            result = subprocess.run(base + [command, str(self.archive), str(path)] + tail,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)['expected_content_matched'])
        self.pack([('docs/a', b'HELLO'), self.items[1]])
        result = subprocess.run(base + ['inspect', str(self.archive), str(path)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(json.loads(result.stdout)['ok'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
