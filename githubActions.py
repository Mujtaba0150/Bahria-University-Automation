from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError
import sys
import os

from functions import (
    ENROLLMENT_NUMBER, PASSWORD, NTFY_SERVER, NOTIFICATION_LEVEL, DOWNLOAD_ASSIGNMENTS,
    start_browser, get_page, close_browser,
    login_to_cms, is_survey_pending, go_to_lms,
    fetch_assignments, build_deadline_notifications, send_deadline_notifications,
    fetch_attendance, send_notification,
)

def check_and_login(page: Page):
    """
    @brief Authenticates user and ensures proper LMS access for assignment retrieval.
    @param page The Playwright page object to interact with.
    @return None
    """
    login_to_cms(page)

    if is_survey_pending(page):
        print("Please complete the Quality Assurance Survey to proceed.")
        send_notification(NTFY_SERVER, "Error", "Please complete the Quality Assurance Survey to proceed.", 2)
        sys.exit(0)

    go_to_lms(page)

def alert_attendance(page: Page, debug_mode: bool):
    """
    @brief Sends a notification for every subject whose absences have exceeded the allowed limit.
    @param page The Playwright page object (logged into CMS).
    @param debug_mode Boolean flag to enable debug output.
    @return None
    """
    for record in fetch_attendance(page, debug_mode):
        if record.remaining < 0:
            send_notification(
                NTFY_SERVER,
                f"Attendance Alert: {record.subject}",
                f"Your attendance for {record.subject} has exceeded the allowed absence limit.",
                5,
            )
            print(f"Notification sent for {record.subject}")

def validate_environment() -> bool:
    """
    @brief Checks that all required environment variables are set, reporting any problems.
    @return True if the configuration is valid.
    """
    problems = []
    if ENROLLMENT_NUMBER == "":
        problems.append("ENROLLMENT_NUMBER is not set.")
    if PASSWORD == "":
        problems.append("PASSWORD is not set.")
    if NOTIFICATION_LEVEL < 0 or NOTIFICATION_LEVEL > 4:
        problems.append("NOTIFICATION_LEVEL must be an integer between 0 and 4.")
    if NTFY_SERVER == "":
        problems.append("NTFY_SERVER is not set.")

    if problems:
        print("Error: One or more required environment variables are not set or are incorrectly set.")
        for problem in problems:
            print(problem)
        if NTFY_SERVER != "":
            send_notification(NTFY_SERVER, "Error", "Error: One or more required environment variables are not set or are incorrectly set.", 3)

    return not problems

def main():
    if not validate_environment():
        return

    try:
        with sync_playwright() as p:
            context = start_browser(p)
            page = get_page(context)

            check_and_login(page)
            download_dir = os.environ.get("HOME") if DOWNLOAD_ASSIGNMENTS else None
            assignments = fetch_assignments(page, download_dir)
            send_deadline_notifications(NTFY_SERVER, build_deadline_notifications(assignments), attach_files=True)
            alert_attendance(page, debug_mode=False)

            close_browser(context)
    except PlaywrightTimeoutError as e:
        print("Operation timed out. The LMS or CMS might be down or unresponsive.")
        send_notification(NTFY_SERVER, "Timeout Error", f"Operation timed out. The LMS or CMS might be down or unresponsive.\nError Details: {str(e)}", 4)
        sys.exit(1)
    except Exception as e:
        print(f"Error during automation: {str(e)}")
        send_notification(NTFY_SERVER, "Error", f"Error during automation: {str(e)}", 4)
        sys.exit(1)

if __name__ == "__main__":
    main()
    # Errors are reported through ntfy, so always exit successfully to keep the workflow run green