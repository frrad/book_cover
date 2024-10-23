## What does it do?

Given a JPG cover spread, generates PDFs for front, back, spine suitable for
printing.

1. trim the provided jpg to front, back, spine to allow for some variance
   between art and book dimensions
1. stretch the trimmed parts to the exact target dimensions
1. join them back together
1. add bleed by stretchign the border
1. split back into three
1. convert to PDF
1. mark the bleed area in the PDF metadata

## Usage

To invoke, run
```
./cover.py --cover_spread spread.jpg
```

Many values are hardcoded, but it should be easy to expose them as parameters if
necessary. Send PRs!


## Setup

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
