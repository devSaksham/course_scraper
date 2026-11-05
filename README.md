# Course Scraper

Scrapes five Coventry University postgraduate course pages and writes one structured JSON record per course: duration, intakes, fees, entry and English-language requirements, required documents and scholarships. The data comes straight from `coventry.ac.uk`, parsed with Requests and BeautifulSoup.

The output schema is the one used for study-abroad course comparison (IELTS/PTE/TOEFL minimums, GPA, backlogs, Class 12 boards, and so on).

## Run it

Python 3.10+.

```bash
git clone https://github.com/devSaksham/course_scraper.git
cd course_scraper
pip install -r requirements.txt
python scraper.py
```

It fetches each page with a 2-second pause between requests and writes `courses.json`. A sample output from a previous run is already committed.

## Courses covered

Data Science MSc, Cyber Security MSc, Civil Engineering MSc, Advanced Mechanical Engineering MSc and Antimicrobial Resistance MSc (2025-26 intake). Edit `COURSE_URLS` in `scraper.py` to change them, or switch `main()` to `discover_course_urls()`, which crawls the university's A-Z postgraduate list.

## How fields are filled

| Source | Fields |
|---|---|
| Scraped from the page | course name (`<h1>`), study level, duration, intakes, tuition fee, scholarships, IELTS/PTE/TOEFL minimums (regex over the entry-requirements section), minimum UG classification, required documents, English waiver via medium of instruction |
| Fixed values | university name, country, campus address |
| `"NA"` | fields Coventry doesn't publish on course pages: GRE/GMAT, Duolingo, Kaplan, Class 12 boards and marks, gap years, backlogs, work experience |

## Failure handling

- A page that fails to load (timeout, 4xx, 5xx) is logged to stderr and replaced by a record with `"NA"` everywhere, so the run always finishes with five records.
- Fields the parser can't find fall back to `""` or `"NA"` instead of raising.
- Duplicate URLs are skipped.

## Files

```
scraper.py        the scraper
courses.json      output
requirements.txt  requests, beautifulsoup4
```
