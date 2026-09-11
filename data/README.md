# Versioned Dictionary Inputs

The proof uses authorized NWL23 and CSW24 KWG files supplied for this project.
Dictionary binaries and complete word exports are deliberately absent from the
review archive. Obtain the relevant lexicons through authorized channels.

The reproduction driver requires these exact SHA-256 hashes:

| File | SHA-256 |
|---|---|
| `NWL23.kwg` | `3e74af981fdd974e107283f686da0fe4b7ec84ad0d825d444330c338c33b91ba` |
| `CSW24.kwg` | `62ca7a84f07429a9976f77a4f74b94911aca5d49cce050dce72dd0e032c0566f` |

Place them in this directory. A KWG re-encoding of the same lexicon may have a
different binary hash; it is not silently accepted as the certified input.
The exported sorted word files have these SHA-256 hashes:

- NWL23: `5254d44586c3af6a8530427b14ef0251af5aa47906ce32a45e4c229261b1456b`
- CSW24: `5646ebbca6b1d5e57459ec431ee81aa8f627e81ab121fe9c7a815221cb727912`

Official edition information is available from
[NASPA](https://www.scrabbleplayers.org/w/NWL2023) and
[WESPA](https://wespa.org/wp-content/uploads/2024/09/CSW24CompleteNewWords.pdf).
The WESPA document is a new-word supplement, not the complete CSW24 input.

Do not place dictionary files in a public Git repository or assume that the
software's MIT license grants redistribution rights in the dictionaries.
