#!/usr/bin/env python3
"""Build the journal upload PDFs without running any proof search."""
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
MONTHLY = ROOT / "monthly"
SUBMISSION = ROOT / "submission"
ENV = dict(os.environ, TEXINPUTS=".:../vendor//:")


def run(command, log_name):
    with (MONTHLY / log_name).open("w") as log:
        subprocess.run(
            command,
            cwd=MONTHLY,
            env=ENV,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
        )


def build_bibliographic(stem):
    run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", f"{stem}.tex"],
        f"{stem}_build1.txt")
    run(["bibtex", stem], f"{stem}_bibliography_build.txt")
    for pass_number in (2, 3):
        run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", f"{stem}.tex"],
            f"{stem}_build{pass_number}.txt")


def build_plain(stem):
    for pass_number in (1, 2):
        run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", f"{stem}.tex"],
            f"{stem}_build{pass_number}.txt")


def main():
    build_bibliographic("manuscript")
    build_bibliographic("manuscript_with_author")
    build_plain("cover_letter")
    build_plain("supplementary_material")

    SUBMISSION.mkdir(exist_ok=True)
    outputs = {
        "manuscript_anonymous.pdf": MONTHLY / "manuscript.pdf",
        "manuscript_with_author.pdf": MONTHLY / "manuscript_with_author.pdf",
        "cover_letter.pdf": MONTHLY / "cover_letter.pdf",
        "supplementary_material.pdf": MONTHLY / "supplementary_material.pdf",
    }
    for name, source in outputs.items():
        shutil.copyfile(source, SUBMISSION / name)
        print(SUBMISSION / name)


if __name__ == "__main__":
    main()
