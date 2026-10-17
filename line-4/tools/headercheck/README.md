# HeaderCheck

Find response-header contract changes before upgrading an OpenAPI integration. Python standard library only; no installation or network is needed. From the repository root:

```sh
python3 -B line-4/tools/headercheck/headercheck.py demo
```

Tried successfully: five operations compared, one potential break and one inherited metadata review, exit 0. The demo starts from the bundled real public IMD description, adds a **hypothetical** required budget header, then makes it optional in a second in-memory copy. Neither header declaration is an observed service promise. No described operation is called.

Compare two workspace JSON descriptions:

```sh
python3 -B line-4/tools/headercheck/headercheck.py compare line-4/tools/apidelta/imd-openapi.json line-4/live-openapi-32.json
```

Both descriptions ship with this round. They matched byte for byte when fetched, and the comparison returned zero findings across five operations. This is historical evidence, not a claim that the live service never changes. Supply your own old/new workspace JSON files for an actual migration.

Compare exits 0 for no detected break, 1 for a potential break, 2 for refused input/error, and 3 for unresolved review. Demo exits 0 after confirming the expected finding. Compare reports include SHA-256 hashes of the input bytes. The Python entry point `compare(old_dict, new_dict)` returns the same report without hashes and does not mutate its inputs.

## What it checks

For common inline top-level paths operations and **exactly matching response status keys**, HeaderCheck:

- Matches ASCII HTTP header names case-insensitively and rejects ambiguous duplicate spellings.
- Reports removal of a required response header or weakening `required: true` to false/absent as a potential break. Removal of an optional header, and any new header, require review.
- Compares common header schemas in the **response** direction using all inherited schema analyzers: new output must remain within the old client's declared output contract. A new enum value can break; removing an enum value alone does not.
- Resolves local Header, Response and Schema Object references, including unchanged references whose targets changed.
- Compares single-media-type header `content` schemas, reviews switches between `schema` and `content`, and reviews simple-style `explode` changes for schema-based headers. Omitted `style`, `explode` and `required` use their header defaults (`simple`, false, false).
- Gives header-specific annotation/extension review locations even when only a referenced Header Object changes.

All IdCheck and earlier findings remain intact, including broad response/document metadata warnings. Therefore case-only spelling or explicit equivalent defaults may still produce an inherited **review**. `Content-Type` entries are ignored by this extension, as specified for response header maps; inherited metadata checks can still mention their textual changes.

The [OpenAPI 3.1 Header Object](https://spec.openapis.org/oas/v3.1.0.html#header-object) says: “The Header Object follows the structure of the Parameter Object with the following changes”. It prohibits `name` and `in` and restricts location-dependent traits to headers. See also the [Response Object](https://spec.openapis.org/oas/v3.1.0.html#response-object) and [Parameter Object](https://spec.openapis.org/oas/v3.1.0.html#parameter-object). The official specification was read during this round.

## Refusals and limits

Header maps, including added/removed statuses of a common operation, are structurally checked before a report is returned. Supported headers must have exactly one `schema` or `content`, simple style, and boolean flags. Empty/multiple-media `content`, invalid HTTP names, non-header parameter fields (`name`, `in`, `allowReserved`, `allowEmptyValue`), external/unresolved/cyclic references and semantic reference siblings are refused. No reference URL is fetched. Header schema *structure* is checked, but this remains a partial OpenAPI/JSON Schema analyzer, not complete validation.

Bounds: 256 headers per response map, 256 characters per header name, and 20,000 resolved non-Content-Type header visits across both inputs. Inherited bounds include 1 MiB per input file, 50,000 nodes, depth 80, 20,000 schema comparisons, 2,000 findings, operation identifier limits and finite server/security budgets. Keep the sibling tools from ApiDelta through IdCheck; imports use explicit adjacent paths. No third-party dependency is required.

Status fallback/range equivalence (`default`, `2XX`, `200`), headers on added/removed operations, callbacks, webhooks, trailers, repeated header lines, value coalescing, actual wire serialization, cookie parsing, CORS exposure and runtime guarantees are outside this extension's scope. A header marked optional can still be important to a particular client; review its removal. A clean report is not proof of runtime or generated-client compatibility. No coin, wallet, credential, payment or deployment is involved.

## Checks performed

```sh
python3 -B line-4/tools/headercheck/selftest.py
python3 -B line-4/check-32.py
```

15 new tests passed, including an independent 36-pair output-state oracle, casing/defaults, optional/required presence, Content-Type exclusion, local and refused references, content schemas, encoding review, invalid structures, limits, precise escaped pointers, inherited finding retention, deterministic nonmutation and all compare CLI outcomes. All 171 inherited tests also passed: **186 tests across 12 suites**. Results are in `line-4/check-results-32.json`.

The optional `python3 -B line-4/check-32.py --live` fetches only the public description at `https://api.imd.fun/openapi.json` with an explicit User-Agent, saves a bounded capture, and compares it. It was run successfully this round; no described service operation was invoked. The default check is fully offline and writes only its round check report (plus temporary scratch used by inherited tests).
