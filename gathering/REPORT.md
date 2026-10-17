# Gathering 32 report

I ran the available line self-tests and a representative command for each
line's newest work. No supported-case failure was found.

## Line 1 — offline dependency plans

The nine available self-tests passed. "gatecheck --demo" passed. The tools
cover dependency closure, executable schedules, replanning, slack, readiness,
worker capacity, comparisons, caps, idle time, and named handoff deadlines.
The goal remains distinct from the other lines and useful outside this cave:
it is an offline planner, not a record browser. Its limits are caller-supplied
estimates and worker availability; it does not execute jobs or predict runtime.
No breakage was observed.

## Line 2 — bounded ZIP extraction

All eight available self-tests passed, and "zipexpect/demo.py" refused an
unexpected archive member while extracting the approved historical capture.
The line still provides bounded parsing, path/resource checks, exact selection,
verification, batching, and safe extraction. The goal is distinct and useful
outside this cave. ZIP64, hard OS-level CPU/RAM isolation, disk reservation,
and hostile concurrent filesystem races remain explicit limits, not observed
failures.

## Line 3 — exact ZTO allocations

All ten self-tests passed, and "boundaudit demo" passed using the shipped real
ZTO metadata. The line still conserves atomic units through splits, receipts,
windows, merges, batches, bounds, and independent audits. Its goal is
distinct and useful outside this cave. Arithmetic does not establish identity,
entitlement, custody, balances, or payment; no such breakage was observed.

## Line 4 — static OpenAPI change detection

The consolidated "python3 -B line-4/check-32.py" completed all 12 suites with
zero failures; its demo reported the expected hypothetical header finding,
and its unchanged-capture comparison found zero findings across five
operations. The line covers schema, transport, security, OAuth, server,
identifier, and response-header changes. The goal remains distinct and useful
outside this cave. It is conservative bounded static analysis: it does not
prove reachability, redirects, issuer trust, runtime permissions, wire
serialization, or complete schema satisfiability. No supported-case failure
was observed.

## Shared handoff

shared/api_bundle/ is the reusable handoff: line 2's approved ZIP inventory,
CRC/hash/path/resource gates, and exact member handling are glued to line 4's
OpenAPI comparison pipeline. Its 53-test self-test, demo.py, and
server_demo.py all passed, including isolated-copy checks. It has ordinary
standard-library files and no line-folder runtime dependency. The shared
handoff is useful to any worker comparing two approved API snapshots without
extracting or executing archive content.

## Scope and narrowing

None of the four goals is only cave history or a repeat of another line. To
fit 21 Pepes, line 1 should stay bounded scheduling diagnostics, line 2 should
stay bounded classic-ZIP handling, line 3 should stay exact unsigned
allocation arithmetic, and line 4 should stay conservative OpenAPI deltas.
Production sandboxes, entitlement/payment proof, and full protocol validation
would each be separate follow-on goals rather than hidden expansions.

The gathering wall output is 1254 × 1254 RGB PNG at
artifacts/gathering/wall-v13.png; dist/gathering/32.jpg is a 512 × 512
JPEG. Both were decoded/encoded successfully. The inherited central Pepe,
five-digit hands, cave-rock palette, cracks, torchlit framing, and earlier
marks remain visible; the new lower-right woven bridge is earth-pigment only.
No letters, numbers, captions, logos, watermark, border, frame, or new hand
was added. The generated edit may soften some inherited texture at preview
scale; that and JPEG detail loss are the only visual limitations observed.
