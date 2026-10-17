#!/usr/bin/env python3
"""Offline delivery checks, adversarial cases, and seeded conservation trials."""
import copy
import itertools
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
import batchintake as bi


class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.request = bi.rs.read_json(bi.rr.ROOT / 'example.json')
        self.metadata = bi.rs.read_json(bi.rr.ROOT / 'zto-mainnet.json')
        self.report = bi.rs.allocate(self.request, self.metadata)
        self.bundle = bi.rb.build(self.request, self.report, self.metadata, 1)

    def check(self, delivery):
        return bi.check(self.request, self.report, self.metadata, self.bundle, delivery)

    def test_all_subsets_and_orders(self):
        for size in range(4):
            for numbers in itertools.permutations([1, 2, 3], size):
                result = self.check(bi.select(self.bundle, list(numbers)))
                self.assertEqual(result['missing_batches'], sorted(set([1, 2, 3]) - set(numbers)))
                self.assertEqual(result['status'], 'complete' if size == 3 else 'incomplete')
                self.assertEqual(result['received_rows'] + result['missing_rows'], 3)
                self.assertEqual(int(result['received_units']) + int(result['missing_units']), 10**18)

    def test_empty(self):
        result = self.check(bi.select(self.bundle, []))
        self.assertEqual(result['received_units'], '0')
        self.assertEqual(result['missing_units'], str(10**18))

    def test_same_report_different_partition(self):
        other = bi.rb.build(self.request, self.report, self.metadata, 2)
        with self.assertRaisesRegex(bi.rs.Invalid, 'another bundle'):
            self.check(bi.select(other, [1]))

    def test_changed_source(self):
        delivery = bi.select(self.bundle, [1])
        self.report['budget_units'] = '2'
        with self.assertRaises(bi.rs.Invalid):
            self.check(delivery)

    def test_wrong_packet_even_rehashed(self):
        delivery = bi.select(self.bundle, [1])
        packet = delivery['packets'][0]
        packet['allocations'][0]['units'] = '3'
        packet['units'] = '3'
        packet['rows_sha256'] = bi.rr.digest(packet['allocations'])
        with self.assertRaisesRegex(bi.rs.Invalid, 'differs'):
            self.check(delivery)

    def test_duplicate(self):
        delivery = bi.select(self.bundle, [1])
        delivery['packets'] *= 2
        with self.assertRaisesRegex(bi.rs.Invalid, 'duplicate'):
            self.check(delivery)

    def test_types_and_extra_fields(self):
        for number in [True, False, 1.0, '1', 0, -1, 4, None, [], {}]:
            delivery = bi.select(self.bundle, [1])
            delivery['packets'][0]['number'] = number
            with self.subTest(number=number), self.assertRaises(bi.rs.Invalid):
                self.check(delivery)
        for key, value in [('extra', 1), ('schema', 'other'), ('packets', {}),
                           ('bundle_sha256', None)]:
            delivery = bi.select(self.bundle, [1])
            delivery[key] = value
            with self.subTest(key=key), self.assertRaises(bi.rs.Invalid):
                self.check(delivery)
        delivery = bi.select(self.bundle, [1])
        delivery['packets'][0]['row_count'] = True
        with self.assertRaises(bi.rs.Invalid):
            self.check(delivery)

    def test_packet_bounds_and_shapes(self):
        for packets in [[None], [1], [dict()], [self.bundle['batches'][0]] * 4]:
            delivery = bi.select(self.bundle, [])
            delivery['packets'] = packets
            with self.assertRaises(bi.rs.Invalid):
                self.check(delivery)

    def test_selection_validation_and_copy(self):
        for numbers in [[1, 1], [True], [0], [4], ['1'], None]:
            with self.assertRaises(bi.rs.Invalid):
                bi.select(self.bundle, numbers)
        delivery = bi.select(self.bundle, [1])
        delivery['packets'][0]['units'] = '0'
        self.assertNotEqual(self.bundle['batches'][0]['units'], '0')

    def test_zero_rows_are_missing_even_with_all_units(self):
        self.request = {'budget': '0.000000000000000001', 'contributors': [
            {'id': 'a', 'weight': '1'}, {'id': 'b', 'weight': '0'}]}
        self.report = bi.rs.allocate(self.request, self.metadata)
        self.bundle = bi.rb.build(self.request, self.report, self.metadata, 1)
        result = self.check(bi.select(self.bundle, [1]))
        self.assertEqual(result['missing_units'], '0')
        self.assertEqual(result['missing_rows'], 1)
        self.assertEqual(result['status'], 'incomplete')

    def test_seeded_partitions(self):
        rng = random.Random(30)
        for trial in range(150):
            count = rng.randint(1, 40)
            units = bi.rs.UINT256_MAX if trial == 0 else rng.randint(1, 10**30)
            self.request = {'budget': bi.rs.display_units(units, 18), 'contributors': [
                {'id': 'role%03d' % n, 'weight': str(rng.randint(1, 99))} for n in range(count)]}
            self.report = bi.rs.allocate(self.request, self.metadata)
            self.bundle = bi.rb.build(self.request, self.report, self.metadata, rng.randint(1, 12))
            numbers = list(range(1, self.bundle['batch_count'] + 1))
            rng.shuffle(numbers)
            numbers = numbers[:rng.randint(0, len(numbers))]
            result = self.check(bi.select(self.bundle, numbers))
            expected_rows = [row for n in numbers for row in self.bundle['batches'][n-1]['allocations']]
            self.assertEqual(result['received_units'], str(sum(int(r['units']) for r in expected_rows)))
            self.assertEqual(result['received_rows'], len(expected_rows))
            self.assertEqual(int(result['received_units']) + int(result['missing_units']), units)

    def test_cli_and_strict_reader(self):
        scratch = Path.cwd() / 'test' / 'scratch'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as temp:
            root = Path(temp)
            for name, obj in [('request', self.request), ('report', self.report), ('bundle', self.bundle),
                              ('delivery', bi.select(self.bundle, [3, 1, 2]))]:
                (root / (name + '.json')).write_text(json.dumps(obj))
            cmd = [sys.executable, '-B', str(Path(bi.__file__)), 'check']
            for name in ['request', 'report', 'bundle', 'delivery']:
                cmd += ['--' + name, str(root / (name + '.json'))]
            run = lambda c: subprocess.run(c, capture_output=True, text=True)
            self.assertEqual(run(cmd).returncode, 0)
            (root / 'delivery.json').write_text(json.dumps(bi.select(self.bundle, [2])))
            result = run(cmd)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(json.loads(result.stdout)['missing_batches'], [1, 3])
            output = root / 'new.json'
            self.assertEqual(run(cmd + ['--output', str(output)]).returncode, 1)
            self.assertEqual(run(cmd + ['--output', str(output)]).returncode, 2)
            (root / 'delivery.json').write_text('{"schema":1,"schema":2}')
            self.assertEqual(run(cmd).returncode, 2)
            select = [sys.executable, '-B', str(Path(bi.__file__)), 'select', '--bundle',
                      str(root / 'bundle.json'), '--numbers', '3', '1']
            self.assertEqual(run(select).returncode, 0)
            self.assertEqual(run(select + ['1']).returncode, 2)


if __name__ == '__main__':
    unittest.main()
