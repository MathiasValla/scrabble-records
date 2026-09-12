# Monthly Submission Checklist

Status: **scientific package complete; author metadata pending**.

Official sources checked again on 12 September 2026:
- https://maa.org/publication/the-american-mathematical-monthly/
- https://maa.org/guide-for-referees/
- the August 2025 `README Author Instructions.pdf` and article template from
  the Monthly's Templates and Styleguide bundle;
- https://maa.org/wp-content/uploads/2025/10/Revised_Figure_Instructions2025.pdf
- https://authorservices.taylorandfrancis.com/publishing-your-research/writing-your-paper/enhancing-your-article-with-supplementary-material/

The journal asks for original exposition that is clear, engaging, and inviting
to mathematicians who are novices in the subject. It uses double-anonymous
review. Taylor & Francis calls the companion file **Supplementary Material**.

## Completed

- English article in the official `maa-monthly.sty`, 12 letter-size pages,
  anonymous and including references. The author-identifying title page remains
  a separate submission item.
- Abstract under 250 words; results ordered from one tile through seven.
- Scrabble rules, board coordinates, tile supply, premiums, scoring, and the
  role of the dictionary are defined for a new reader.
- A formal completeness proposition links every exhaustive stage to a necessary
  condition on a real move. Exact integer and rational bounds are proved in the
  text; the audit counts are consolidated in one table.
- Both dictionary word sets are identified by sizes and SHA-256 hashes.
- Fourteen attaining histories, all independently replayed, establish equality.
- `monthly/supplementary_material.pdf`, 15 pages, begins with a rules and
  certificate guide, followed by one board and its complete tile-placement
  history per page. Dense histories use at least 8-point type.
- Both PDFs were compiled without overfull boxes, all fonts are embedded, and
  every page was rendered for visual review.
- The public source exporter is allowlisted and omits licensed dictionaries,
  private notes, build logs, and obsolete simulation material.

## Required Before Upload

- Supply author-confirmed name, affiliation, city, country, email, corresponding
  author, funding, contribution, conflict, and short biography information.
- Generate the named manuscript and cover letter from those declarations.
- Confirm originality and concurrent-submission status in the cover letter.
- Upload the board/history PDF as **Supplementary Material for review**. Upload
  source code and certificate data through the review portal or an anonymous
  archival link; the public GitHub repository identifies its owner.
- Confirm the active Taylor & Francis submission route on the day of submission.

The two reports generated during development are internal adversarial mock
reviews. They must not be presented as journal referee reports. The MAA's
current referee policy expressly forbids appointed reviewers from using
generative AI on unpublished manuscripts.
