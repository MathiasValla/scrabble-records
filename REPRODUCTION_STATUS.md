# Scrabble record audit, 2026-09-11

The attached conversation is a research lead, not an execution certificate.
Its numerical claims will be reproduced before being promoted to theorems.

## Correction to the existing six-tile proof

`legal_product_search.py` rejects nonwords on a partial scoring board. This is
not a necessary condition for completion: omitted support tiles can extend a
nonword into a legal word. The corresponding upper-bound claim in the old
six-tile article has been replaced by the repaired proof described below. The 1723-point
construction and independent-cross bound are separate claims and are unaffected
by this logical issue. Earlier five-tile and smaller bounds did not use that
rejection rule.

Completion-safe rejection must consider every dictionary word that could contain
the forced run, or use a still more permissive relaxation. Connectivity of the
pre-move board and reachability from an opening are distinct obligations.

## Scope

Reproduce k=1 and k=2 first for the local NWL23 and CSW24 KWG files, then extend
the common proof to k=3..7. All maxima concern ordinary move scores, excluding
challenge/time penalties and endgame rack adjustments. A lower-bound witness
requires an explicitly legal construction; an upper bound may search a superset.

The previous NWL23 target vector is 213, 459, 882, 1130, 1401, 1723, 1786.
Only results with new execution evidence are labeled reproduced.

## Reproduced in this revision

NWL23 k=1..7: 213, 459, 882, 1130, 1401, 1723, 1786.
CSW24 k=1..7: 225, 483, 912, 1349, 1478, 1721, 1787.

The four small-case witnesses include complete physical rack/draw streams. All
NWL23 k=1..6 boards use at most 86 tiles, so the manuscript's sparse-history
lemma also supplies racks for the larger certificates.

The six-tile upper bound is repaired in `repair_six_upper.py`: all twenty
bag-feasible threshold products are eliminated, four by uncompletable rows and
sixteen by the impossible mandatory X hook. The obsolete checker is not used.

The seven-tile independent scan reproduces 82937692 raw index sets, 22137382
deletion-valid sets, 1187919660 placements, and 87 survivors. The complete later
chain has now been independently reproduced: 3748 scoring products, 255
row-compatible products, 34 singleton-hook-compatible products, 193 reduced
boards, 24293 connecting cores, 5518820 assignments, no surviving completion.
The 193-board sets agree by coordinates; the supplied serialization order and
byte hash did not reproduce. The 97-tile attainment has an explicit two-player
deal, pass, draw, and endgame certificate in `verify_seven_racks.py`.

CSW24 k=3,4,5 attaining histories use 65, 72, and 81 physical tiles. The
four-tile upper proof excludes all three independent-bound survivors at 1350.
For five tiles, twelve main placements above 1478 yield ten bag-feasible scoring
products; all ten force H8 empty, impossible after any legal opening. The
attaining construction uses PENNYWORTH, with its Y blank, and scores 1478.
CSW24 k=6 now has the exact maximum 1721. A complete threshold-1722 scan and product search leave 15,809
products: 12,457 fail row completion, 3,345 fail mandatory singleton hooks,
and the last seven fail shared-bag completion. `verify_csw_six_upper.py`
rechecks these stages. The new early bag-row relaxation passes adversarial
toy-completion tests; the unchanged NWL23 hook path still produces the same
canonical 193-board set. A 93-tile attaining board adds the two middle O's of
TOOT to connect two components. A bounded reverse search finds a 25-move setup;
`verify_csw_six.py` replays it independently, assigns blanks at D6 and I4,
and checks the complete two-player rack stream. Player B reserves the last
seven-tile PACIFYING setup move.

CSW24 k=7 is now exact at 1787. The independently verified 96-tile witness has
27 setup moves. Its rack is ABEOPXZ, with blank A at C2 and blank M at F3;
neither blank belongs to any scored word. Adding T at M9 and R at N9 to reduced
base 43801 (rank 66, record 6840 of the threshold-1737 discovery run) forms TETRI
and connects the last component. The fixed board is now in
`find_csw_seven_history.py`; its uncapped reverse search finds a history, and
`verify_csw_seven.py` binds an independent forward/rack replay to the upper bound.

As an additional verifier regression,
`build_csw_seven_baseline.py` postpones the X from the six-tile board to the
final turn, adding XED's eleven points and the bingo. A new 23-move setup and
full two-player certificate are checked by `verify_csw_seven_witness.py`.
The chosen blanks are A at C2 and N at I4. Corruption tests independently reject
altered scores, new-square indices, pre-final boards, and setup words.
The uncapped threshold-1738 scan covers 2,038,152,480 placements and retains
168. Complete products leave 420,538 patterns: 408,785 fail permissive row
completion, 11,731 fail mandatory singleton hooks, and thirteen force H8 empty.
The last nine all fail the shared-bag completion search. A fresh streaming
recheck is implemented by `verify_csw_seven_upper.py`. The separate uncapped
threshold-1737 discovery search completed under `output/jobs/csw24_seven_1737/`:
171 main survivors, 912,147 products, 39 necessary-test survivors, and two
nonempty base families of 660,898 and 359 boards. A short-core discovery probe
found the TETRI connection. Its restricted search is used only to find a witness,
never as an exclusion proof. Every optimality exclusion comes from the complete
threshold-1738 run. All final scored words exist in NWL23, but JACULATIONS, the
required predecessor of EJACULATIONS, does not; this is the decisive dictionary
obstruction to importing this construction.

The distribution study now consists of 1,000 completed cooperative-model games
per dictionary, with a fixed master seed. `build_sampling_figure.py` independently
replays all 2,000 histories, physical bags, rack streams, and sampled scores.
It rejects incomplete studies. Seven ECDF panels, sample sizes, and simultaneous
model-based DKW band widths are in the article. These are not tournament data.

## Reproduction

Run `python3 scripts/reproduce_release.py` for fresh computations from the exact
KWG inputs. C++17, Python 3.10+, NumPy, and SciPy are required. SciPy proposes
letter prices; only integer certificates prove exclusions. The release runs in
minutes on the local machine; logs are saved per step under
`output/reproduction/logs/`. The driver includes all fourteen cases and applies
no time cap to the resource searches. The much larger attaining-board discovery
is separate and need not be rerun to verify the fixed witness.

`--check-existing` checks artifacts and constructions but is deliberately labeled
as NOT an exhaustive rerun. To build the manuscript after verification:

```sh
python3 scripts/build_monthly_figures.py
python3 scripts/build_sampling_figure.py
python3 scripts/build_monthly.py
```

The official Monthly template and its dependencies are fetched separately from
hash-verified publisher and CTAN archives; they are not redistributed. The PDF covers
all seven cases in both dictionaries. The source conversation is evidence
about proposed methodology, not authority for numerical proof claims.

## Input count distinction

NWL23 contains 212868 entries in this KWG, of which 196601 have length 2..15.
The attached audit first disputed the larger count, then explicitly corrected
itself. Both counts should be reported with their meanings.

## Clean release verification

On 2026-09-11, the minimal public source package was exported to a clean directory
with an initially empty output tree. A fresh exhaustive run completed in
1345.947 seconds (22 minutes 26 seconds), reproducing all fourteen exact maxima
and leaving no pending cases. The atomic run record includes source hashes,
per-step logs and timings, and the final result hash. Generated certificate
boards were rebuilt from these fresh results. The final 19-page manuscript and
16-page board atlas were rendered and visually reviewed.

Licensed dictionary inputs remain external. Public continuous integration runs
dictionary-free adversarial tests, not the full numerical proof. The latter
requires the precisely identified authorized inputs. Author declarations remain
necessary before journal submission.
