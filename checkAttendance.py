from playwright.sync_api import sync_playwright, Page
import argparse
import sys

from functions import (
    ENROLLMENT_NUMBER, PASSWORD, USER_DATA_DIR, CHECK_UPDATES, CMS_ATTENDANCE_URL,
    check_for_updates, format_number,
    start_browser, get_page, close_browser, handle_script_error,
    ensure_cms_login, is_survey_pending, fetch_attendance,
)

def display_attendance(page: Page, debug_mode: bool):
    """
    @brief Displays how many more classes can be missed in each subject, highlighting those close to the limit.
    @param page The Playwright page object (logged into CMS).
    @param debug_mode Boolean flag to enable debug output.
    @return None
    """
    for record in fetch_attendance(page, debug_mode):
        remaining = f"{format_number(record.remaining)}/{record.maximum}"
        if record.remaining <= 2:
            remaining = f"\033[1;91m{remaining}\033[0m"
        print(f"\033[1;97m{record.subject}\033[0m: {remaining}")

def parse_args():
    """
    @brief Parses command-line arguments for the attendance checker.
    @return Parsed arguments object with debug option.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug mode")
    return parser.parse_args()

if __name__ == "__main__":
    try:
        if ENROLLMENT_NUMBER == "" or PASSWORD == "" or USER_DATA_DIR == "":
            print("Error: ENROLLMENT_NUMBER, PASSWORD, and USER_DATA_DIR must be set in the .env file.")
            sys.exit(1)

        args = parse_args()
        context = None

        with sync_playwright() as p:
            try:
                context = start_browser(p, USER_DATA_DIR, headless=not args.debug)
                page = get_page(context)
                ensure_cms_login(context, page, CMS_ATTENDANCE_URL, args.debug)

                if is_survey_pending(page):
                    print("Please complete the Quality Assurance Survey to proceed (run fillSurveys.py).")
                    sys.exit(1)

                display_attendance(page, args.debug)
                close_browser(context)
            except Exception as e:
                handle_script_error(e, context, "checkAttendance")
                sys.exit(1)

        if CHECK_UPDATES:
            check_for_updates()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)
