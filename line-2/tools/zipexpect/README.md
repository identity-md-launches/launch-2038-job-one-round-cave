# ZipExpect — admit only the expected package

ZipExpect checks an untrusted ZIP against an independently supplied exact list
of file paths, byte lengths and SHA-256 hashes before publishing an extraction.
A safely named extra file is still refused. Explicit directories are allowed
only when they are ancestors of an expected file; extra empty directories are
refused. An empty file list accepts only an empty archive.

From the repository root, this command shows it working without installation
or network access:

```sh
python3 -B line-2/tools/zipexpect/demo.py
```

When tried in round 32, the demonstration refused an added `unexpected.py`
without creating an output directory, then extracted 23,132 byte-identical
bytes from the shipped historical public IMD OpenAPI capture. The capture's
hard-coded hash is checked before packing. This is an offline replay, not an
observation of today's API. No ZIP content is executed.

The implementation uses only Python's standard library and the committed
sibling ZipGate and SafeZip modules. Keep those sibling folders when copying
this tool. No ZTO, IMD, wallet, payment or network access is needed.

## Use with your package

Prepare a trusted JSON policy with exactly this structure (the example hash is
the real SHA-256 of the five ASCII bytes `hello`):

```json
{"files":[{"path":"docs/a","bytes":5,"sha256":"2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"}]}
```

Then inspect or extract, using paths within the current workspace:

```sh
python3 -B line-2/tools/zipexpect/zipexpect.py inspect package.zip expected.json
python3 -B line-2/tools/zipexpect/zipexpect.py extract package.zip expected.json unpacked --seconds 10
```

`unpacked` must be absent with an existing parent. Success prints JSON and
returns 0; validation failures print `ok: false` JSON and return 2. CLI usage
errors return argparse's status 2. File order is irrelevant; path spelling is
exact. Uppercase SHA-256 input is accepted and normalized. Duplicate JSON keys,
unknown policy fields, malformed values, unsafe or colliding paths are refused.

Default limits: 1 MiB policy JSON, 1,000 ZIP entries and expected files, 2 MiB
central directory, 32 MiB archive, 32,000 filesystem nodes, 16 MiB per file,
64 MiB total uncompressed bytes, compression ratio 200. The corresponding CLI
flags are `--policy-bytes`, `--entries`, `--directory-bytes`, `--archive-bytes`,
`--nodes`, `--file-bytes`, `--total-bytes`, and `--ratio`. `--sha256` optionally
pins the input ZIP digest as well. All are positive integers. Policies may
expect zero-length files. `--seconds` sets a finite positive cooperative budget
across policy validation, both archive passes, matching and staged publication;
CLI policy-file reading occurs before this budget begins. The Python API adds
`cancelled=callable` and accepts the same archive-limit keyword arguments.

ZipGate bounds the central directory before Python parses it. SafeZip checks
all paths, payload hashes and CRCs under the resource limits. ZipExpect compares
the full checked inventory before calling extraction. Extraction takes a fresh
bounded snapshot and requires the same archive hash before parsing or staging,
so a replacement archive between review and publication is refused.

## Checks and limits

```sh
python3 -B line-2/tools/zipexpect/selftest.py
```

All 24 tests passed: exact extraction, added/missing/changed files, unexpected
empty directories, explicit parents, empty packages, policy validation and
collisions, bounded policy reading, archive limits and approvals, replacement
between passes, interruption, preserved existing output and CLI success/failure.
The inherited 28 ZipGate tests also passed unchanged.

A policy obtained from the same untrusted package adds no authenticity. Obtain
it through a trusted channel; this tool verifies neither signatures nor the
provenance of expected values. Matching content may still be malicious to run.
Budgets are cooperative, not hard CPU/RAM isolation or disk reservation.
ZIP64 and unsupported layouts remain refused. Extraction needs a cooperative
local filesystem with no hostile concurrent path mutations; this is not a
sandbox for competing local processes. It checks and extracts bytes, not
ownership, permissions, timestamps or application behavior.
