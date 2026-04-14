# Coventry University Course Scraper

Pulls structured data for 5 postgraduate courses directly from
[coventry.ac.uk](https://www.coventry.ac.uk). No third-party platforms, no
pre-existing datasets — just the official university pages.

---

## What it does

The scraper hits five course pages on the Coventry University website, parses
each one with BeautifulSoup, and writes the result to `courses.json`. Every
URL in the code is a canonical `coventry.ac.uk` URL, so the data source
requirement is fully satisfied.

The five courses scraped:

| # | Course | URL |
|---|--------|-----|
| 1 | Data Science MSc | `/course-structure/pg/ees/data-science-msc/` |
| 2 | Cyber Security MSc | `/course-structure/pg/ees/cyber-security-msc/` |
| 3 | Civil Engineering MSc | `/course-structure/pg/ees/civil-engineering-msc/` |
| 4 | Advanced Mechanical Engineering MSc | `/course-structure/pg/ees/advanced-mechanical-engineering-msc/` |
| 5 | Antimicrobial Resistance MSc | `/course-structure/pg/ees/antimicrobial-resistance-msc/` |

---

## Requirements

- Python 3.10 or newer
- `requests` — HTTP client
- `beautifulsoup4` — HTML parser

---

## Setup

**1. Clone / copy the project folder**

```bash
cd coventry_scraper
```

**2. Create a virtual environment (recommended but optional)**

```bash
python -m venv .venv
source .venv/bin/activate      # macOS / Linux
.venv\Scripts\activate         # Windows
```

**3. Install dependencies**

```bash
pip install requests beautifulsoup4
```

That's it. The scraper only uses the standard library plus those two packages.

---

## How to run

```bash
python scraper.py
```

You'll see a line printed for each URL as it's fetched:

```
Coventry University Course Scraper
========================================
Target: 5 courses

  Scraping: https://www.coventry.ac.uk/course-structure/pg/ees/data-science-msc/?term=2025-26
  Scraping: https://www.coventry.ac.uk/course-structure/pg/ees/cyber-security-msc/?term=2025-26
  ...

Done. 5 records written to courses.json
```

The script pauses 2 seconds between requests. Five courses take roughly
10–15 seconds total.

---

## Output format

`courses.json` is a JSON array of exactly 5 objects. Each object follows
the required schema:

```json
[
  {
    "program_course_name": "Data Science MSc",
    "university_name": "Coventry University",
    "course_website_url": "https://www.coventry.ac.uk/...",
    "campus": "Coventry",
    "country": "United Kingdom",
    "address": "Priory Street, Coventry, CV1 5FB, United Kingdom",
    "study_level": "Postgraduate",
    "course_duration": "1 year full-time; up to 2 years with placement",
    "all_intakes_available": "March 2026; May 2026; July 2026",
    "mandatory_documents_required": "Academic transcripts; two references; ...",
    "yearly_tuition_fee": "...",
    "scholarship_availability": "...",
    "gre_gmat_mandatory_min_score": "NA",
    "indian_regional_institution_restrictions": "NA",
    "class_12_boards_accepted": "NA",
    "gap_year_max_accepted": "NA",
    "min_duolingo": "NA",
    "english_waiver_class12": "NA",
    "english_waiver_moi": "...",
    "min_ielts": "IELTS 6.0 overall with no component below 5.5",
    "kaplan_test_of_english": "NA",
    "min_pte": "NA",
    "min_toefl": "NA",
    "ug_academic_min_gpa": "2:2 undergraduate degree ...",
    "twelfth_pass_min_cgpa": "NA",
    "mandatory_work_exp": "NA",
    "max_backlogs": "NA"
  },
  ...
]
```

### Field notes

**Fields populated from the page**
- `program_course_name` — scraped from the `<h1>` tag
- `course_duration` — from the "Course features" sidebar
- `all_intakes_available` — start dates listed in the sidebar
- `study_level` — extracted from the "Study level" label on each page
- `min_ielts`, `min_pte`, `min_toefl` — regex-extracted from the entry
  requirements section
- `ug_academic_min_gpa` — pulled from the degree classification mentioned in
  entry requirements (e.g. "2:2 undergraduate degree")
- `mandatory_documents_required` — list items found in the requirements section

**Fields set to static values**
- `university_name` — always "Coventry University"
- `country` — always "United Kingdom"
- `address` — Coventry campus address (Priory Street, CV1 5FB)

**Fields that return `"NA"`**
Some fields (GRE/GMAT scores, Duolingo minimums, backlog limits, class 12
details) are not published on Coventry's postgraduate course pages. Where the
university provides that information, it's typically on the country-specific
entry requirements page rather than the individual course page. Those fields
are returned as `"NA"` rather than guessed.

---

## How course URLs were found

The five URLs in `COURSE_URLS` were discovered by browsing the official A-Z
postgraduate listing at:

```
https://www.coventry.ac.uk/study-at-coventry/postgraduate-study/az-course-list/
```

The scraper also includes a `discover_course_urls()` function that can crawl
this listing page automatically if you want to expand coverage beyond 5
courses. It's not called by default — just change `main()` to use it if needed.

---

## Edge cases and error handling

- **Network failure** — if a page can't be fetched (timeout, 4xx, 5xx), the
  scraper logs a warning to stderr and writes a skeleton record with `"NA"` in
  every field, so the run still completes and always produces exactly 5 records.
- **Missing fields** — any field the parser can't find on a page defaults to
  `""` or `"NA"`. The scraper never crashes on missing content.
- **Duplicate URLs** — guarded against in the main loop. Won't be an issue
  with the fixed list, but it's there if you switch to dynamic URL discovery.
- **Rate limiting** — a 2-second delay between requests keeps load on the
  server low and avoids triggering any rate limiter.

---

## Project structure

```
coventry_scraper/
├── scraper.py       # main scraper — run this
├── courses.json     # output (generated when you run scraper.py)
└── README.md        # this file
```
