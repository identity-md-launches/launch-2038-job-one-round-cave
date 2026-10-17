# BatchIntake

Check a partial or out-of-order delivery of RewardBatch review files against the original exact ZTO allocation. The result names the missing batches and gives exact received/missing contributor counts and atomic units. Missing zero-unit rows still make a delivery incomplete. Every supplied packet must match its canonical source batch, including fields, JSON types, rows and hashes; duplicated packet numbers are rejected rather than silently deduplicated.

From the repository root, with Python 3.9+ and only its standard library:

```sh
python3 -B line-3/tools/batchintake/batchintake.py demo
```

Expected exit **0**. The address-free illustrative example uses the inherited historical real Ethereum ZTO metadata capture. Receiving only batch 2 leaves batch 1 missing: 333333333333333333 units received and 666666666666666667 missing. Receiving batches 2 then 1 is complete: all three contributors and exactly 1000000000000000000 units (1 ZTO). No live chain request is needed.

Keep the sibling RewardBatch, RewardReceipt and RewardSplit folders together. First obtain REQUEST.json, REPORT.json and BUNDLE.json with those tools. Keep the original request, token capture and allocation through your trusted review process. Then package a selection for an offline handoff:

```sh
python3 -B line-3/tools/batchintake/batchintake.py select \
  --bundle BUNDLE.json --numbers 2 1 --output DELIVERY.json
python3 -B line-3/tools/batchintake/batchintake.py check \
  --request REQUEST.json --report REPORT.json --bundle BUNDLE.json \
  --delivery DELIVERY.json
```

`select` copies the named batches in the supplied order and links the envelope to the canonical SHA-256 of the entire source bundle. It packages data; it does not verify that source. `check` verifies the original allocation and complete bundle with RewardReceipt/RewardBatch, checks the envelope's bundle link, and compares each packet to its source. Different batch sizes produce different bundle links even for the same allocation. An empty `--numbers` selection is supported. The envelope is exactly `{"schema":"batchintake-delivery-v1","bundle_sha256":"…","packets":[…]}`; packets are verbatim batch objects, not new allocation calculations.

For a different token capture, add `--metadata CAPTURE.json` to `check`; it must be the same capture used for the original allocation. ZTO is the default; inherited metadata validation also accepts IMD. The snapshot is historical and is not refreshed by this tool.

Exit codes: **0** complete (or successful select/demo), **1** valid but incomplete delivery, **2** invalid input or I/O failure. A status JSON is emitted for exits 0 and 1. Invalid deliveries produce no status. `--output` writes a new workspace file and refuses overwrites. Inputs reject duplicate JSON keys and non-finite numbers, and input/output JSON is bounded to 256 KiB. No input path may resolve outside the current workspace. The source allocator supports at most 1,000 contributors; larger bundles may hit its smaller effective serialized-size limit.

What happened here: the demo returned 0 with the exact totals above. All **12 tests** passed, covering all ordered subsets of a three-batch bundle, wrong-source links, source-report mutation, rehashed altered packets, duplicate delivery, malformed types and extra fields, copy isolation, zero-unit missing rows, 150 seeded partitions including uint256 maximum, CLI exit codes, duplicate keys and overwrite refusal. The inherited RewardBatch suite also passed all 11 tests.

```sh
python3 -B line-3/tools/batchintake/selftest.py
```

This checks review-file completeness within one supplied delivery. It does not track deliveries across runs, prevent payment replay, approve work, establish identity/entitlement or prove custody, balances or payment. Hash links are unsigned; replacing every original input can create a different valid allocation. Nothing accesses environment settings, secrets, wallets, signs, sends, pays or posts. No network or installation is needed.
