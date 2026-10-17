#!/usr/bin/env python3
"""Offline response-header regression tests and finite contract oracle."""
import contextlib
import copy
import io
import itertools
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import headercheck as h


def header(required=False, values=None):
    result = {'schema': {'type': 'integer'}, 'required': required}
    if values is not None:
        result['schema']['enum'] = values
    return result


def doc(headers=None):
    return {'openapi': '3.1.0', 'paths': {'/a~b/c': {'get': {
        'operationId': 'read', 'responses': {'200': {'description': 'OK', 'headers': headers or {}}}}}}}


def codes(a, b):
    return {f['code'] for f in h.compare(a, b)['findings']}


class Checks(unittest.TestCase):
    def test_capture_demo(self):
        capture = Path(__file__).resolve().parents[1] / 'apidelta/imd-openapi.json'
        a, _ = h.api.load(capture)
        self.assertEqual(h.compare(a, a)['findings'], [])
        self.assertEqual(h.demo()['counts'], {'breaking': 1, 'review': 1, 'info': 0})

    def test_presence_value_oracle(self):
        # Enumerate possible old/new output states, independent of analyzer rules.
        # A new output outside the old output contract is a potential break.
        variants = list(itertools.product((False, True), ([0], [1], [0, 1])))
        for (oreq, oval), (nreq, nval) in itertools.product(variants, repeat=2):
            with self.subTest(old=(oreq, oval), new=(nreq, nval)):
                old_states = set(oval) | (set() if oreq else {'absent'})
                new_states = set(nval) | (set() if nreq else {'absent'})
                result = h.compare(doc({'X-Budget': header(oreq, oval)}),
                                   doc({'X-Budget': header(nreq, nval)}))
                self.assertEqual(bool(result['counts']['breaking']), not new_states <= old_states)

    def test_header_removed_added(self):
        for required in (False, True):
            a = doc({'X-Budget': header(required)})
            result = h.compare(a, doc())
            item = next(f for f in result['findings'] if f['code'] == 'response_header_removed')
            self.assertEqual(item['severity'], 'breaking' if required else 'review')
            self.assertIn('response_header_added', codes(doc(), a))

    def test_case_insensitive_default_and_content_type(self):
        a = doc({'X-Budget': {'schema': {'type': 'integer'}}})
        b = doc({'x-budget': {'style': 'simple', 'explode': False,
                              'required': False, 'schema': {'type': 'integer'}}})
        # Broad inherited metadata review remains, but no new semantic warning.
        result = h.compare(a, b)
        self.assertFalse(any(f['code'].startswith('response_header_') for f in result['findings']))
        a = doc({'Content-Type': {'$ref': 'https://example.invalid/never-read'}})
        b = doc({'content-type': False})
        self.assertEqual(h.compare(a, b)['header_visits'], 0)

    def test_duplicate_invalid_names(self):
        for mapping in ({'X-A': header(), 'x-a': header()}, {'bad name': header()},
                        {'': header()}, {'雪': header()}, {'a' * 257: header()}):
            with self.subTest(mapping=mapping), self.assertRaises(h.api.Invalid):
                h.compare(doc(mapping), doc(mapping))

    def test_invalid_header_structures(self):
        bad = [False, [], None, {}, {'schema': {}, 'content': {}}, {'schema': 1},
               {'schema': {}, 'required': 'yes'}, {'schema': {}, 'explode': 1},
               {'schema': {}, 'deprecated': None}, {'schema': {}, 'style': 'form'},
               {'schema': {}, 'name': 'X'}, {'schema': {}, 'in': 'header'},
               {'schema': {}, 'allowReserved': False}, {'schema': {}, 'allowEmptyValue': False},
               {'content': {}}, {'content': {'a': {}, 'b': {}}}, {'content': {'a': None}},
               {'content': {'a': {'schema': 1}}}]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(h.api.Invalid):
                h.compare(doc({'X': value}), doc({'X': value}))
        for value in (None, [], False):
            a = doc()
            a['paths']['/a~b/c']['get']['responses']['200']['headers'] = value
            with self.assertRaises(h.api.Invalid):
                h.compare(a, a)

    def test_local_header_and_schema_references(self):
        a = doc({'X': {'$ref': '#/components/headers/Budget'}})
        a['components'] = {'headers': {'Budget': {'schema': {'$ref': '#/components/schemas/Budget'}}},
                           'schemas': {'Budget': {'type': 'integer', 'enum': [1]}}}
        b = copy.deepcopy(a)
        b['components']['schemas']['Budget']['enum'] = [1, 2]
        self.assertIn('schema_enum_incompatible', codes(a, b))
        b = copy.deepcopy(a)
        b['components']['headers']['Budget']['deprecated'] = True
        self.assertIn('response_header_metadata_changed', codes(a, b))

    def test_reference_refusals(self):
        for ref in ('https://example.invalid/never-read', '#/missing', '#/components/headers/Loop'):
            a = doc({'X': {'$ref': ref}})
            a['components'] = {'headers': {'Loop': {'$ref': '#/components/headers/Loop'}}}
            with self.subTest(ref=ref), self.assertRaises(h.api.Invalid):
                h.compare(a, a)

    def test_response_reference(self):
        a = doc()
        response = a['paths']['/a~b/c']['get']['responses']['200']
        response['headers'] = {'X': header(True)}
        a['components'] = {'responses': {'OK': response}}
        a['paths']['/a~b/c']['get']['responses']['200'] = {'$ref': '#/components/responses/OK'}
        b = copy.deepcopy(a)
        b['components']['responses']['OK']['headers'] = {}
        self.assertIn('response_header_removed', codes(a, b))

    def test_content_direction_and_representation(self):
        a = doc({'X': {'content': {'application/json': {'schema': {'type': 'integer', 'enum': [1]}}}}})
        b = copy.deepcopy(a)
        b['paths']['/a~b/c']['get']['responses']['200']['headers']['X']['content'][
            'application/json']['schema']['enum'] = [1, 2]
        self.assertIn('schema_enum_incompatible', codes(a, b))
        self.assertIn('response_header_representation_changed', codes(a, doc({'X': header()})))

    def test_explode_and_metadata(self):
        a, b = doc({'X': header()}), doc({'X': dict(header(), explode=True)})
        self.assertIn('response_header_encoding_changed', codes(a, b))
        b = doc({'X': dict(header(), description='Client-visible description')})
        self.assertIn('response_header_metadata_changed', codes(a, b))

    def test_status_and_operation_scope(self):
        a, b = doc({'X': header(True)}), doc({'X': header(True)})
        responses = b['paths']['/a~b/c']['get']['responses']
        responses['201'] = responses.pop('200')
        found = codes(a, b)
        self.assertIn('response_status_changed', found)
        self.assertNotIn('response_header_removed', found)
        # The new extension validates added/removed status headers on common operations.
        responses['201']['headers'] = {'X': {}}
        with self.assertRaises(h.api.Invalid):
            h.compare(a, b)
        a = doc()
        a['webhooks'] = {'event': {'post': {'responses': {'200': {'headers': {'X': {}}}}}}}
        self.assertEqual(h.compare(a, a)['header_visits'], 0)

    def test_bounds(self):
        a = doc({'X': header()})
        with patch.object(h, 'MAX_HEADERS', 0), self.assertRaises(h.api.Invalid):
            h.compare(a, a)
        with patch.object(h, 'MAX_HEADER_VISITS', 1), self.assertRaises(h.api.Invalid):
            h.compare(a, a)

    def test_inherited_retention_nonmutation_and_pointer(self):
        a, b = doc({'X~Budget': header(True)}), doc({'X~Budget': header(False)})
        b['paths']['/a~b/c']['get']['operationId'] = 'renamed'
        snapshot = copy.deepcopy((a, b))
        result = h.compare(a, b)
        self.assertTrue(all(f in result['findings'] for f in h.ids.compare(a, b)['findings']))
        self.assertEqual((a, b), snapshot)
        self.assertEqual(h.compare(a, b), result)
        self.assertTrue(any(f['location'] == '/paths/~1a~0b~1c/get/responses/200/headers/x~0budget/required'
                            for f in result['findings']))

    def test_cli_outcomes_in_memory(self):
        pairs = [(doc(), doc(), 0), (doc({'X': header(True)}), doc(), 1),
                 (doc(), doc({'X': header()}), 3), (doc({'X': {}}), doc(), 2)]
        for old, new, expected in pairs:
            out, err = io.StringIO(), io.StringIO()
            with patch.object(h.api, 'load', side_effect=[(old, 'a' * 64), (new, 'b' * 64)]), \
                    contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                exit_code = h.main(['compare', 'old.json', 'new.json'])
            self.assertEqual(exit_code, expected, err.getvalue())
            if expected == 2:
                self.assertEqual(out.getvalue(), '')
            else:
                self.assertEqual(json.loads(out.getvalue())['old_sha256'], 'a' * 64)


if __name__ == '__main__':
    unittest.main()
