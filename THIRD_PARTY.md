# Licensing and Attribution

The MIT license applies to this project's Python/C++ software, tests, small
certificate fixtures, and software documentation. It does not relicense the
research manuscript, third-party packages, dictionaries, or trademarks.

- The NWL23 and CSW24 dictionaries are external licensed inputs. Neither their
  binaries nor their complete word exports or cross-option domains are in this
  repository. See `data/README.md` for hashes and edition information.
- The NWL23 1786-point construction is attributed to Bob Lucassen (2024) in
  the article. Reproducing it here is not a claim to have discovered it.
- DejMar reported a 1787-point Collins construction in the Scrabulizer comments
  in 2016, clarifying the dictionary as CSW15 in 2018. This earlier report is
  cited in the article; the CSW24 proof does not claim that numerical score as new.
- The corrected seven-tile tail and its small fixtures originate in the
  project owner's supplied research notes. The production chain recomputes
  the preceding reductions and checks equality of canonical board sets.
- The official Monthly style and bibliography files belong to their respective
  authors. They are fetched from the MAA template archive, not redistributed
  or relicensed by this repository.
- Scrabble and its TeX dependencies are fetched as complete, unchanged CTAN
  archives. They retain their original notices and licenses (chiefly LPPL).
  `scripts/fetch_tex_dependencies.py` pins archive hashes. None is committed.
- NumPy, SciPy, Pillow, TeX Live, and Poppler are external dependencies with
  their own licenses. The repository does not bundle their implementations.
- Scrabble is a trademark of its respective owners. This independent research
  project is not affiliated with or endorsed by them or by the MAA.

The manuscript and its generated figures/PDFs are supplied for research review;
their publication rights are reserved separately from the software license.
No journal acceptance or endorsement is implied.
