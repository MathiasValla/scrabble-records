# How Much Can a Scrabble Move Score?

Reproducible computer-assisted extremal proofs for the standard 15 by 15
English Scrabble board, with exact dictionary editions NWL23 and CSW24.

| New tiles | NWL23 | CSW24 |
|---:|---:|---:|
| 1 | 213 | 225 |
| 2 | 459 | 483 |
| 3 | 882 | 912 |
| 4 | 1130 | 1349 |
| 5 | 1401 | 1478 |
| 6 | 1723 | 1721 |
| 7 | 1786 | 1787 |

These are ordinary move scores: seven tiles include the 50-point bingo;
challenge bonuses, time penalties, and endgame rack transfers are excluded.
Every attaining certificate includes a legal setup history, permanent blanks,
and physical rack/draw reachability, not just a final diagram. Bob Lucassen's
NWL23 seven-tile construction is reproduced and attributed, not claimed as new.
The Collins score 1787 was already reported by DejMar in the Scrabulizer
discussion in 2016 (clarified as CSW15 in 2018). We certify it for CSW24;
we do not claim priority for that previously reported number.

The English article targets **The American Mathematical Monthly**. It is a
research manuscript, not an accepted paper. See [the manuscript source](monthly/manuscript.tex),
[manuscript PDF](monthly/manuscript.pdf), and
[Supplementary Material](monthly/supplementary_material.pdf).
Author declarations and journal submission steps remain in [the checklist](MONTHLY_SUBMISSION.md).

## Reproduce All Fourteen Maxima

Requirements: Python 3.10+, NumPy, SciPy, and a C++17 compiler (`c++` on PATH).
The development environment used Python 3.10.18 and Apple Clang 16.0.0.
The tested Python dependencies are pinned in `requirements-reproduce.txt`.
Pillow is needed only for optional PDF review contact sheets.

1. Create a virtual environment and install the dependencies.
2. Supply authorized copies of `data/NWL23.kwg` and `data/CSW24.kwg`.
   Their exact expected hashes and edition sources are in [data/README.md](data/README.md).
3. Run the proof driver, without Python's `-O` option or `PYTHONOPTIMIZE`.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-reproduce.txt
python -u scripts/reproduce_release.py
```

The driver exports the dictionaries, compiles both C++ programs, repeats every
exclusion search, runs adversarial tests, and independently replays the
attaining histories. There is **no search time cap**. A full development run
took about 22 minutes; runtime depends on hardware and SciPy's proposed prices.
Allow one driver per checkout. To detach it from a terminal:

```sh
nohup python -u scripts/reproduce_release.py > reproduction.log 2>&1 &
```

Keep the computer awake. Atomic progress is recorded in
`output/reproduction/run_state.json`; individual logs are in
`output/reproduction/fresh_logs/`. Artifact-only checks use the separate
`output/reproduction/existing_check_logs/` directory and cannot overwrite a
fresh run's evidence. Success requires `complete: true`, a matching
result hash, `pending: []`, and all fourteen entries in
`output/reproduction_verified.json`. An older result file alone does not
certify a newer interrupted run. The progress record includes source and log
hashes, step timings, and the Python version.

`--check-existing` is an explicitly labeled artifact check, **not** a fresh
exhaustive run. Discovery of attaining boards need not be repeated: the
fixed witnesses are included and checked forward from legal openings.

## What Proves the Bounds?

The manuscript explains each mathematical relaxation before the computation:
deletion fragments, physical-square blank penalties, independent crosses,
rational resource prices, completion-safe word tests, and connecting cores.
SciPy only proposes nonnegative prices. Integer certificates, not a numerical
solver's status, justify every resource exclusion. There is no SAT dependency.

For NWL23 seven tiles, the complete upper-bound chain is:

```text
1,187,919,660 placements -> 87 independent-bound survivors
-> 3,748 scoring products -> 255 row-compatible products
-> 34 singleton-hook-compatible products -> 193 reduced boards
-> 24,293 connecting cores -> 5,518,820 letter assignments -> 0.
```

For CSW24, exclusion of every seven-tile score above 1787 is:

```text
2,038,152,480 placements -> 168 independent-bound survivors
-> 420,538 scoring products -> 9 necessary-test survivors
-> 0 shared-bag hook completions.
```

The 1787-point attaining board uses 96 tiles and 27 setup moves. A two-letter
bridge forms TETRI. All eight words scored on the final move also belong to
NWL23, but the necessary predecessor JACULATIONS does not. The dictionaries
are not nested, which also explains why the six-tile CSW24 maximum can be lower.

Code map:
- `scan_k_upper.cpp`: common independent-cross scan, k=2..7.
- `search_one_tile.py`: exhaustive one-tile bound.
- `exact_product_search.cpp`, `resource_prices.py`: complete resource products.
- `repair_six_upper.py`, `complete_seven_hooks.py`, `seven_tail/`: completion-safe exclusions.
- `verify_*`: separate construction, rack, and certificate checkers.
- `test_record_bounds.py`, `test_seven_completeness.py`: synthetic adversarial tests.

Public CI runs dictionary-free tests on Python 3.10 and 3.12. It does **not**
prove the numerical maxima: the full proof requires the licensed dictionaries.
This is a computer-assisted proof, not a Lean/Coq formalization.

## Rebuild the Article and Figures

Install a TeX Live distribution with pdfLaTeX, e-TeX, BibTeX, TikZ, AMS packages,
Times fonts, `standalone`, `booktabs`, and `listings`. Poppler (`pdftops`,
`pdfinfo`, `pdftoppm`) is needed for figure exports and visual review.
The following fetches the exact Monthly style and CTAN Scrabble dependencies
from official sources, verifies their archive hashes, and extracts them locally.
It does not install system packages or run with administrator privileges.

```sh
python scripts/fetch_tex_dependencies.py
python scripts/build_monthly_figures.py
python scripts/build_monthly.py
python scripts/export_monthly_figures.py
python scripts/render_monthly.py
```

Run the proof first to regenerate the construction certificates. To typeset
only the already supplied figure sources, the fetch and `build_monthly.py`
commands suffice. The fourteen board/rack figures have
standalone TeX, PDF, and EPS exports in `monthly/figures/exports/`.
Hashes pin the external TeX archives; an upstream change fails closed instead
of silently substituting another dependency version.
The MAA endpoint sometimes rejects automated downloads (HTTP 403). In that
case, use the journal's [Templates and Styleguide link](https://maa.org/publication/the-american-mathematical-monthly/)
to obtain the archive as `tmp/tex_archives/monthly_templates.zip`, then rerun
the fetch command. The cached archive is subject to exactly the same hash check.

## Release Boundary

The source export is allowlisted and recorded in `RELEASE_MANIFEST.json`.
It excludes dictionary binaries, complete word exports, cross-option domains,
private conversations, obsolete filters, build executables, and local logs.
Only three small, hash-linked NWL23 tail fixtures are retained.
The MIT license covers project software; see [THIRD_PARTY.md](THIRD_PARTY.md)
for exclusions, attribution, and separately reserved manuscript rights.
The public GitHub repository is not anonymous: use a metadata-clean review
snapshot if requested by the journal's double-anonymous process.

Verify an unpacked public snapshot before use:

```sh
python scripts/verify_release_manifest.py .
```

For the review archive, pass `--manifest REVIEW_MANIFEST.json` instead.
