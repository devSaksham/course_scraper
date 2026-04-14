"""
Coventry University Course Scraper
-----------------------------------
Pulls structured data for 5 postgraduate courses directly from
https://www.coventry.ac.uk — no third-party sources, no shortcuts.

Run:  python scraper.py
Output: courses.json (5 records, one per course)
"""

import json
import time
import re
import sys
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_URL = "https://www.coventry.ac.uk"

# These 5 course URLs were discovered by crawling the official A-Z postgraduate
# list at /study-at-coventry/postgraduate-study/az-course-list/
# All are canonical coventry.ac.uk pages — no third-party sources.
COURSE_URLS = [
    "https://www.coventry.ac.uk/course-structure/pg/ees/data-science-msc/?term=2025-26",
    "https://www.coventry.ac.uk/course-structure/pg/ees/cyber-security-msc/?term=2025-26",
    "https://www.coventry.ac.uk/course-structure/pg/ees/civil-engineering-msc/?term=2025-26",
    "https://www.coventry.ac.uk/course-structure/pg/ees/advanced-mechanical-engineering-msc/?term=2025-26",
    "https://www.coventry.ac.uk/course-structure/pg/ees/antimicrobial-resistance-msc/?term=2025-26",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; CoventryCourseScraper/1.0; "
        "+https://github.com/your-org/coventry-scraper)"
    )
}

# Pause between requests so we don't hammer the server
REQUEST_DELAY_SECONDS = 2

UNIVERSITY_NAME = "Coventry University"
COUNTRY = "United Kingdom"
ADDRESS = "Priory Street, Coventry, CV1 5FB, United Kingdom"


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def get_page(url: str) -> BeautifulSoup | None:
    """Fetch a URL and return a BeautifulSoup object, or None on failure."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except requests.RequestException as exc:
        print(f"  [warn] Could not fetch {url}: {exc}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

def safe_text(element) -> str:
    """Return stripped text from a BS4 element, or '' if element is None."""
    if element is None:
        return ""
    return element.get_text(separator=" ", strip=True)


def find_section_text(soup: BeautifulSoup, *keywords) -> str:
    """
    Walk headings and paragraphs looking for a block that contains any of the
    given keywords. Returns the text of the next sibling block, or ''.
    """
    for tag in soup.find_all(["h2", "h3", "h4", "strong", "dt"]):
        tag_text = tag.get_text(strip=True).lower()
        if any(kw.lower() in tag_text for kw in keywords):
            # Try the next sibling first
            sibling = tag.find_next_sibling()
            if sibling:
                return safe_text(sibling)
            # Fall back to parent's next sibling
            parent_sib = tag.parent.find_next_sibling() if tag.parent else None
            if parent_sib:
                return safe_text(parent_sib)
    return ""


def extract_course_features(soup: BeautifulSoup) -> dict:
    """
    Parse the 'Course features' sidebar-style box that Coventry uses on every
    course page. Keys include Location, Duration, Study mode, Start date, etc.
    Returns a plain dict of whatever's on the page.
    """
    features = {}
    # The sidebar uses definition-list style markup in some versions,
    # and h3/p pairs in others. We handle both.
    course_box = soup.find("div", class_=re.compile(r"course[-_]feature", re.I))
    if not course_box:
        # Fallback: look for the section that contains "Year of entry"
        for heading in soup.find_all(["h2", "h3"]):
            if "course features" in heading.get_text(strip=True).lower():
                course_box = heading.find_parent(["section", "div", "article"])
                break

    if not course_box:
        return features

    # Collect h3 label -> following p or div value pairs
    for label_tag in course_box.find_all(["h3", "dt", "strong"]):
        label = label_tag.get_text(strip=True).rstrip(":")
        value_tag = label_tag.find_next_sibling(["p", "dd", "div", "span"])
        if value_tag:
            features[label] = safe_text(value_tag)

    return features


def extract_fees(soup: BeautifulSoup) -> str:
    """
    Look for tuition fee figures. Coventry usually shows UK and international
    fees in a table or under a 'Fees and funding' heading.
    """
    # Try a fee table first
    for table in soup.find_all("table"):
        table_text = table.get_text(" ", strip=True)
        if "international" in table_text.lower() or "£" in table_text:
            rows = table.find_all("tr")
            for row in rows:
                cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
                if any("international" in c.lower() for c in cells):
                    return " | ".join(cells)

    # Fall back to scanning paragraphs near a "Fees" heading
    fees_text = find_section_text(soup, "Fees and funding", "Tuition fee", "Course fee")
    if fees_text:
        return fees_text

    # Last-ditch: find the first £ mention
    match = re.search(r"£[\d,]+(?:\s*per year)?", soup.get_text())
    return match.group(0) if match else "NA"


def extract_english_requirements(soup: BeautifulSoup) -> dict:
    """
    Scrape the English language requirements block. Returns a dict with
    ielts, pte, toefl, duolingo, and a raw block for anything else.
    """
    result = {
        "min_ielts": "NA",
        "min_pte": "NA",
        "min_toefl": "NA",
        "min_duolingo": "NA",
        "kaplan_test_of_english": "NA",
    }

    page_text = soup.get_text(" ")

    # IELTS
    ielts_match = re.search(
        r"IELTS[^.]*?(\d+\.?\d*)\s*(?:overall|in each|with no)", page_text, re.I
    )
    if ielts_match:
        result["min_ielts"] = ielts_match.group(0).strip()

    # PTE
    pte_match = re.search(r"PTE[^.]*?(\d+)", page_text, re.I)
    if pte_match:
        result["min_pte"] = pte_match.group(0).strip()

    # TOEFL
    toefl_match = re.search(r"TOEFL[^.]*?(\d+)", page_text, re.I)
    if toefl_match:
        result["min_toefl"] = toefl_match.group(0).strip()

    # Duolingo
    duolingo_match = re.search(r"Duolingo[^.]*?(\d+)", page_text, re.I)
    if duolingo_match:
        result["min_duolingo"] = duolingo_match.group(0).strip()

    # Kaplan
    kaplan_match = re.search(r"Kaplan[^.]{0,80}", page_text, re.I)
    if kaplan_match:
        result["kaplan_test_of_english"] = kaplan_match.group(0).strip()

    return result


def extract_entry_requirements(soup: BeautifulSoup) -> dict:
    """
    Grab the entry requirements section — GPA, work experience, backlogs, etc.
    Returns a dict of raw scraped text for each field.
    """
    result = {
        "ug_academic_min_gpa": "NA",
        "twelfth_pass_min_cgpa": "NA",
        "mandatory_work_exp": "NA",
        "max_backlogs": "NA",
        "mandatory_documents_required": "NA",
        "gre_gmat_mandatory_min_score": "NA",
        "indian_regional_institution_restrictions": "NA",
        "class_12_boards_accepted": "NA",
        "gap_year_max_accepted": "NA",
        "english_waiver_class12": "NA",
        "english_waiver_moi": "NA",
    }

    # Find the entry requirements section
    req_section = None
    for heading in soup.find_all(["h2", "h3"]):
        if "entry requirement" in heading.get_text(strip=True).lower():
            req_section = heading.find_parent(["section", "div", "article"])
            break

    if not req_section:
        return result

    section_text = req_section.get_text(" ", strip=True)

    # Academic level  (e.g. "2:1 undergraduate degree" or "second class degree")
    gpa_match = re.search(
        r"(2:1|2:2|first.class|second.class|bachelor.{0,30}degree)", section_text, re.I
    )
    if gpa_match:
        result["ug_academic_min_gpa"] = gpa_match.group(0).strip()

    # Work experience
    work_match = re.search(
        r"((?:relevant|professional|industry)\s+work\s+experience[^.]{0,100})", section_text, re.I
    )
    if work_match:
        result["mandatory_work_exp"] = work_match.group(0).strip()

    # English waiver (medium of instruction / class 12)
    if re.search(r"english.{0,30}waiver|medium of instruction", section_text, re.I):
        result["english_waiver_moi"] = (
            "English language waiver may be available for students whose previous "
            "studies were conducted in English. See entry requirements page for details."
        )

    # Mandatory documents — grab list items inside the section
    docs = []
    for li in req_section.find_all("li"):
        li_text = li.get_text(strip=True)
        if any(
            kw in li_text.lower()
            for kw in ["transcript", "reference", "personal statement", "passport",
                       "certificate", "english", "cv", "resume", "portfolio"]
        ):
            docs.append(li_text)
    if docs:
        result["mandatory_documents_required"] = "; ".join(docs)

    return result


# ---------------------------------------------------------------------------
# Main scrape function
# ---------------------------------------------------------------------------

def scrape_course(url: str) -> dict:
    """
    Fetch a single Coventry course page and return a fully populated record
    matching the required schema. Missing fields default to 'NA'.
    """
    print(f"  Scraping: {url}")
    soup = get_page(url)

    if soup is None:
        return _empty_record(url)

    # --- Course name ---
    title_tag = soup.find("h1")
    course_name = safe_text(title_tag) if title_tag else "NA"

    # --- Course features sidebar ---
    features = extract_course_features(soup)

    location = features.get("Location", "Coventry University (Coventry)")
    # Strip campus prefix for cleaner campus field
    campus = location.replace("Coventry University", "").strip().strip("()")
    if not campus:
        campus = "Coventry"

    duration = features.get("Duration", features.get("Course duration", "NA"))
    study_mode = features.get("Study mode", "NA")
    start_dates = features.get("Start date", features.get("Start dates", "NA"))

    # Study level
    study_level_tag = soup.find(string=re.compile(r"study level", re.I))
    if study_level_tag:
        parent = study_level_tag.find_parent()
        raw_level = safe_text(parent) if parent else "NA"
        # The page says "Study level: Postgraduate" — grab the bit after the colon
        level_match = re.search(r"study level[:\s]+(.+)", raw_level, re.I)
        study_level = level_match.group(1).strip() if level_match else "Postgraduate"
    else:
        study_level = "Postgraduate"

    # --- Fees ---
    yearly_tuition_fee = extract_fees(soup)

    # --- English requirements ---
    english = extract_english_requirements(soup)

    # --- Entry requirements ---
    entry = extract_entry_requirements(soup)

    # --- Scholarship ---
    scholarship_text = find_section_text(soup, "Scholarship", "Bursary", "Funding")
    if not scholarship_text:
        # Check for any mention of scholarship on the page
        page_text = soup.get_text(" ")
        if re.search(r"scholarship|bursary|discount", page_text, re.I):
            scholarship_text = (
                "Scholarships and bursaries may be available. "
                "See the Fees and Funding section on the course page for details."
            )
        else:
            scholarship_text = "NA"

    record = {
        "program_course_name": course_name,
        "university_name": UNIVERSITY_NAME,
        "course_website_url": url,
        "campus": campus,
        "country": COUNTRY,
        "address": ADDRESS,
        "study_level": study_level,
        "course_duration": duration,
        "all_intakes_available": start_dates,
        "mandatory_documents_required": entry["mandatory_documents_required"],
        "yearly_tuition_fee": yearly_tuition_fee,
        "scholarship_availability": scholarship_text,
        "gre_gmat_mandatory_min_score": entry["gre_gmat_mandatory_min_score"],
        "indian_regional_institution_restrictions": entry["indian_regional_institution_restrictions"],
        "class_12_boards_accepted": entry["class_12_boards_accepted"],
        "gap_year_max_accepted": entry["gap_year_max_accepted"],
        "min_duolingo": english["min_duolingo"],
        "english_waiver_class12": entry["english_waiver_class12"],
        "english_waiver_moi": entry["english_waiver_moi"],
        "min_ielts": english["min_ielts"],
        "kaplan_test_of_english": english["kaplan_test_of_english"],
        "min_pte": english["min_pte"],
        "min_toefl": english["min_toefl"],
        "ug_academic_min_gpa": entry["ug_academic_min_gpa"],
        "twelfth_pass_min_cgpa": entry["twelfth_pass_min_cgpa"],
        "mandatory_work_exp": entry["mandatory_work_exp"],
        "max_backlogs": entry["max_backlogs"],
    }

    return record


def _empty_record(url: str) -> dict:
    """Return a skeleton record when a page can't be fetched."""
    return {
        "program_course_name": "NA",
        "university_name": UNIVERSITY_NAME,
        "course_website_url": url,
        "campus": "NA",
        "country": COUNTRY,
        "address": ADDRESS,
        "study_level": "NA",
        "course_duration": "NA",
        "all_intakes_available": "NA",
        "mandatory_documents_required": "NA",
        "yearly_tuition_fee": "NA",
        "scholarship_availability": "NA",
        "gre_gmat_mandatory_min_score": "NA",
        "indian_regional_institution_restrictions": "NA",
        "class_12_boards_accepted": "NA",
        "gap_year_max_accepted": "NA",
        "min_duolingo": "NA",
        "english_waiver_class12": "NA",
        "english_waiver_moi": "NA",
        "min_ielts": "NA",
        "kaplan_test_of_english": "NA",
        "min_pte": "NA",
        "min_toefl": "NA",
        "ug_academic_min_gpa": "NA",
        "twelfth_pass_min_cgpa": "NA",
        "mandatory_work_exp": "NA",
        "max_backlogs": "NA",
    }


# ---------------------------------------------------------------------------
# URL discovery (bonus utility — not required to run the scraper)
# ---------------------------------------------------------------------------

def discover_course_urls(listing_url: str, limit: int = 5) -> list[str]:
    """
    Crawl Coventry's A-Z postgraduate course listing page and pull out
    individual course page URLs. This is how COURSE_URLS above were found.
    Pass limit=0 to get all URLs without stopping early.
    """
    print(f"Discovering course URLs from: {listing_url}")
    soup = get_page(listing_url)
    if soup is None:
        return []

    found = set()
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        full = urljoin(BASE_URL, href)
        # Coventry course pages sit under /course-structure/pg/ or similar paths
        if "/course-structure/pg/" in full and full not in found:
            found.add(full)
            if limit and len(found) >= limit:
                break

    return list(found)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print("Coventry University Course Scraper")
    print("=" * 40)
    print(f"Target: {len(COURSE_URLS)} courses\n")

    results = []
    seen_urls = set()

    for url in COURSE_URLS:
        # Guard against duplicates — shouldn't happen with a fixed list, but
        # good practice if COURSE_URLS ever gets populated dynamically
        if url in seen_urls:
            print(f"  [skip] Duplicate URL: {url}")
            continue
        seen_urls.add(url)

        record = scrape_course(url)
        results.append(record)

        # Be polite to the server
        time.sleep(REQUEST_DELAY_SECONDS)

    output_path = "courses.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nDone. {len(results)} records written to {output_path}")


if __name__ == "__main__":
    main()
