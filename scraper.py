import logging
import re
import time
import random
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)

# Real PeopleSoft selectors for coursesearch92.ais.uchicago.edu
SELECTORS = {
    "term_dropdown": "#UC_CLSRCH_WRK2_STRM",
    "subject_dropdown": "#UC_CLSRCH_WRK2_SUBJECT",
    "keyword_input": "#UC_CLSRCH_WRK2_PTUN_KEYWORD",
    "search_button": "#UC_CLSRCH_WRK2_SEARCH_BTN",
    "results_count": "#UC_RSLT_NAV_WRK_PTPG_ROWS_GRID",
}

PEOPLESOFT_BASE_URL = "https://coursesearch92.ais.uchicago.edu/"


class PeopleSoftScraper:
    def __init__(self, config):
        self.url = config.get("PEOPLESOFT_URL", PEOPLESOFT_BASE_URL)
        self.headless = config.get("PLAYWRIGHT_HEADLESS", True)

    def start(self):
        logger.info("Scraper initialized (thread-safe mode: fresh browser per search)")

    def stop(self):
        logger.info("Scraper stopped")

    def search_class(self, term, subject, keyword):
        """
        Search PeopleSoft for classes. subject can be empty for all-department search.
        keyword is the search term (course name, number, or instructor).
        Creates a fresh Playwright browser per call for thread safety.
        Returns a list of section dicts with subject/catalog_number extracted per result.
        """
        pw = None
        browser = None
        try:
            pw = sync_playwright().start()
            browser = pw.chromium.launch(headless=self.headless)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            page.set_default_timeout(20000)

            # Navigate to class search
            page.goto(self.url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(5)

            # Select term
            page.wait_for_selector(SELECTORS["term_dropdown"], state="visible", timeout=10000)
            page.select_option(SELECTORS["term_dropdown"], value=term)
            time.sleep(1)

            # Select subject/department (optional — empty string means all departments)
            if subject:
                page.select_option(SELECTORS["subject_dropdown"], value=subject.upper())
                time.sleep(1)

            # Enter keyword in search box
            page.fill(SELECTORS["keyword_input"], keyword)
            time.sleep(1)

            # Click search
            page.click(SELECTORS["search_button"])
            page.wait_for_load_state("domcontentloaded", timeout=30000)
            time.sleep(5)

            # Check for no results
            body_text = page.inner_text("body")
            if "no classes are scheduled" in body_text.lower():
                logger.info(f"No results for {subject or 'ALL'} '{keyword}'")
                return []

            # Extract all results
            results = self._extract_results(page)
            logger.info(f"Found {len(results)} sections for {subject or 'ALL'} '{keyword}'")
            return results

        except PlaywrightTimeout as e:
            logger.error(f"Timeout searching {subject or 'ALL'} '{keyword}': {e}")
            return []
        except Exception as e:
            logger.error(f"Error searching {subject or 'ALL'} '{keyword}': {e}")
            return []
        finally:
            if browser:
                browser.close()
            if pw:
                pw.stop()

    def _extract_results(self, page):
        """Extract class sections from PeopleSoft results using JavaScript."""
        js_code = """() => {
            const results = [];
            const allRows = document.querySelectorAll('[id*="DESCR100"][id*="_row_"]');
            for (const row of allRows) {
                if (row.offsetParent === null) continue;
                const text = row.innerText.trim();
                if (!text) continue;
                results.push(text);
            }
            return results;
        }"""

        row_texts = page.evaluate(js_code)
        results = []

        for text in row_texts:
            parsed = self._parse_result_row(text)
            if parsed:
                results.append(parsed)

        return results

    def _parse_result_row(self, text):
        """
        Parse a result row like:
        'The Elements of Economic Analysis II
         ECON 20100/1 [21669] - LEC In-Person Closed Consent Required
         Section Enrollment: 58/55
         Afonso
         Mon Wed : 01:30 PM-02:50 PM'
        """
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if len(lines) < 2:
            return None

        course_name = lines[0]

        # Parse the section line: "ECON 20100/1 [21669] - LEC In-Person Closed"
        section_line = lines[1] if len(lines) > 1 else ""

        # Extract subject and catalog number from "ECON 20100/1"
        course_id_match = re.match(r"([A-Z]+)\s+(\d+)/(\d+)", section_line)
        if course_id_match:
            subject = course_id_match.group(1)
            catalog_number = course_id_match.group(2)
            section = course_id_match.group(3)
            course_id = f"{subject} {catalog_number}/{section}"
        else:
            subject = ""
            catalog_number = ""
            section_match = re.search(r"/(\d+)", section_line)
            section = section_match.group(1) if section_match else "1"
            course_id = section_line

        # Extract class number from [XXXXX]
        class_nbr_match = re.search(r"\[(\d+)\]", section_line)
        class_nbr = class_nbr_match.group(1) if class_nbr_match else ""

        # Determine open/closed status
        status = "Unknown"
        if re.search(r"\bClosed\b", section_line, re.IGNORECASE):
            status = "Closed"
        elif re.search(r"\bOpen\b", section_line, re.IGNORECASE):
            status = "Open"

        # Parse enrollment from "Section Enrollment: 58/55"
        enrolled, capacity = 0, 0
        for line in lines:
            enrl_match = re.search(r"Section Enrollment:\s*(\d+)/(\d+)", line)
            if enrl_match:
                enrolled = int(enrl_match.group(1))
                capacity = int(enrl_match.group(2))
                break

        # Extract instructor name (usually line after enrollment)
        instructor = ""
        schedule = ""
        for i, line in enumerate(lines):
            if "Section Enrollment" in line and i + 1 < len(lines):
                instructor = lines[i + 1]
            if re.search(r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun)", line):
                schedule = line

        return {
            "section": section,
            "subject": subject,
            "catalog_number": catalog_number,
            "course_name": course_name,
            "course_id": course_id,
            "class_nbr": class_nbr,
            "enrolled": enrolled,
            "capacity": capacity,
            "status": status,
            "instructor": instructor,
            "schedule": schedule,
        }

    def check_classes(self, class_list, jitter=True):
        """
        Check a batch of classes. class_list is [(term, subject, catalog_number), ...].
        Returns dict keyed by (subject, catalog_number, term) with list of section results.
        """
        all_results = {}
        for term, subject, catalog_number in class_list:
            results = self.search_class(term, subject, catalog_number)
            all_results[(subject, catalog_number, term)] = results
            if jitter and len(class_list) > 1:
                time.sleep(random.uniform(2, 5))
        return all_results
