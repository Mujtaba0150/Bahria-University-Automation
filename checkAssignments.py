from playwright.sync_api import sync_playwright, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError
import subprocess
import argparse
import sys
import os
import glob

from functions import (
    ENROLLMENT_NUMBER, PASSWORD, USER_DATA_DIR, DOWNLOAD_DIR, CHECK_UPDATES, SCRIPT_DIR,
    CMS_LOGIN_URL, CMS_LOGOFF_URL, LMS_ASSIGNMENTS_URL, LMS_SIGNOUT_URL,
    Assignment, clear_terminal, check_for_updates, format_day_month,
    start_browser, get_page, close_browser, handle_script_error,
    login_to_cms, select_institution, wait_for_login, is_survey_pending, go_to_lms, persist_cookies,
    fetch_assignments, build_deadline_notifications, send_deadline_notifications,
)

class Colors:
    RED_BRIGHT = "\x1b[38;2;255;0;0m"
    YELLOW_BRIGHT = "\x1b[38;2;251;255;0m"
    YELLOW_MEDIUM = "\x1b[38;2;255;241;49m"
    YELLOW_DARK = "\x1b[38;2;245;228;0m"
    GREEN_BRIGHT = "\x1b[38;2;25;189;25m"
    GREEN_MEDIUM = "\x1b[38;2;12;131;12m"
    GREEN_DARK = "\x1b[38;2;9;92;9m"
    RESET = "\033[0m"

subject_abbreviations = {
    "Computer Architecture Lab": "CA Lab",
    "Operating Systems Lab": "OS Lab",
    "Design and Analysis of Algorithms Lab": "DAA Lab",
    "Artificial Intelligence Lab": "AI Lab",
    "Design and Analysis of Algorithms": "DAA",
    "Theory of Automata": "TOA",
    "Operating Systems": "OS",
    "Computer Architecture": "CA",
    "Artificial Intelligence": "AI"
}

def parse_args():
    """
    @brief Parses command-line arguments for the assignment checker.
    @return Parsed arguments object with kde, ntfy, download_assignments, whatsapp, debug and login options.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-k", "--kde", action="store", help="Send notifications via KDE Connect using Device ID")
    parser.add_argument("-N", "--ntfy", action="store", help="Send notifications via Ntfy using Server")
    parser.add_argument("-n", action="store_false", dest="download_assignments", help="Don't download assignments")
    parser.add_argument("-w", "--whatsapp", action="store_true", help="Format for WhatsApp Message")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("-l", "--login", action="store_true", help="Enable login mode")
    return parser.parse_args()

def rerun_self(context: BrowserContext, extra_args: list[str], drop_args: tuple = ()):
    """
    @brief Closes the browser and re-runs this script with adjusted arguments, then exits.
    The browser must be closed first, otherwise the child process can't open the same profile.
    @param context The BrowserContext to close.
    @param extra_args Arguments to add.
    @param drop_args Arguments to remove.
    @return None (exits)
    """
    close_browser(context)
    args = [a for a in sys.argv[1:] if a not in drop_args]
    subprocess.run([sys.executable, os.path.abspath(__file__), *extra_args, *args])
    sys.exit(0)

def check_and_login(context: BrowserContext, page: Page, debug_mode: bool, login_mode: bool):
    """
    @brief Handles user login and ensures proper authentication before accessing assignments.
    @param context The BrowserContext (used for cookies and restarting).
    @param page The Playwright page object to interact with.
    @param debug_mode Boolean flag to enable debug output.
    @param login_mode Boolean flag to indicate if the user is logging in manually.
    @return None
    """
    page.goto(LMS_ASSIGNMENTS_URL, wait_until="commit")

    if "https://lms.bahria.edu.pk/" in page.url:
        logged_in_enrollment_number: str = page.locator("body > div > header > nav > div > ul > li.dropdown.user.user-menu > ul > li.user-header > p").text_content().strip()  # type: ignore[union-attr]
        if ENROLLMENT_NUMBER not in logged_in_enrollment_number:
            if debug_mode:
                print("Logged in with a different account. Logging out...")

            page.goto(LMS_SIGNOUT_URL, wait_until="commit")
            page.goto(CMS_LOGOFF_URL, wait_until="commit")
            check_and_login(context, page, debug_mode, login_mode)
        else:
            print(f"Logged in as {ENROLLMENT_NUMBER}" if ENROLLMENT_NUMBER else "Logged in")
        return

    page.goto(CMS_LOGIN_URL)
    if "Login.aspx" in page.url:
        if ENROLLMENT_NUMBER != "" and PASSWORD != "":
            login_to_cms(page)

        elif not login_mode:
            # No saved credentials: restart in a visible window so the user can log in
            rerun_self(context, ["--login"])

        else:
            # Manual login: the user signs in through the visible browser window
            print("Please log in through the browser window (waiting up to 2 minutes)...")
            select_institution(page)
            try:
                wait_for_login(page, timeout=120000)
            except PlaywrightTimeoutError:
                print("Failed to log in, please enter your username and password.")
                sys.exit(1)
            print("Logged in")
    else:
        print(f"Logged in as {ENROLLMENT_NUMBER}" if ENROLLMENT_NUMBER else "Logged in")

    if is_survey_pending(page):
        print("Please complete the Quality Assurance Survey to proceed.")
        run_qa_survey(context)

    go_to_lms(page)
    persist_cookies(context, debug_mode)

    if login_mode:
        # Chromium writes cookies to disk in batches, so closing right after saving them can lose
        # them. Give it a moment before closing so the next (headless) run finds the session.
        page.wait_for_timeout(3000)
        # Re-run normally (headless) now that the session is saved
        rerun_self(context, [], drop_args=("-l", "--login"))

def run_qa_survey(context: BrowserContext):
    """
    @brief Prompts user to run automated survey filling script.
    The LMS can't be reached until the survey is completed, so this always exits afterwards.
    @param context The BrowserContext to close before handing over to fillSurveys.py.
    @return None (exits)
    """
    print("Do you want to run the script to fill the survey automatically? (y/n): ", end="")
    choice = input().strip().lower()
    if choice == 'y':
        survey_file_path = os.path.join(SCRIPT_DIR, "fillSurveys.py")
        if os.path.exists(survey_file_path):
            # Close our browser first so fillSurveys.py can open the same profile
            close_browser(context)
            clear_terminal()
            subprocess.run([sys.executable, survey_file_path])
            print("Surveys done. Run checkAssignments.py again to fetch your assignments.")
            sys.exit(0)
        else:
            print("Survey automation script not found.")
    sys.exit(1)

def cleanup_old_files(download_dir: str, keep_paths: list[str], debug_mode: bool):
    """
    @brief Deletes downloaded assignment files that are no longer active, then removes empty folders.
    @param download_dir The root directory containing downloaded assignments.
    @param keep_paths Paths of files belonging to current assignments.
    @param debug_mode Boolean flag to enable debug output.
    @return None
    """
    keep_files = {os.path.normcase(os.path.normpath(path)) for path in keep_paths}

    for path in glob.glob(os.path.join(glob.escape(download_dir), "**", "*"), recursive=True):
        if os.path.isdir(path):
            continue
        if os.path.normcase(os.path.normpath(path)) not in keep_files:
            try:
                os.remove(path)
                if debug_mode:
                    print(f"Deleted file: {path}")
            except Exception as e:
                print(f"Error deleting {path}: {e}")

    # Remove empty directories
    for root, dirs, _ in os.walk(download_dir, topdown=False):
        for d in dirs:
            full_path = os.path.join(root, d)
            if not os.listdir(full_path):
                try:
                    os.rmdir(full_path)
                    if debug_mode:
                        print(f"Deleted empty directory: {full_path}")
                except Exception as e:
                    print(f"Error deleting directory {full_path}: {e}")

def display_whatsapp_formatted_deadlines(assignments: list[Assignment]):
    """
    @brief Formats and displays assignment deadlines in WhatsApp-friendly format.
    @param assignments The assignments returned by fetch_assignments().
    @return None
    """
    for assignment in sorted(assignments, key=lambda a: a.deadline_date):
        short_subject = subject_abbreviations.get(assignment.subject, assignment.subject)
        day = assignment.deadline_date.day
        suffix = "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        print(f"{short_subject} - {day}{suffix} {assignment.deadline_date.strftime('%b')}")

def display_deadlines(assignments: list[Assignment], KDE_device: str, ntfy_server: str):
    """
    @brief Displays assignment deadlines with color coding and sends notifications.
    @param assignments The assignments returned by fetch_assignments().
    @param KDE_device KDE Connect device ID for notifications.
    @param ntfy_server Ntfy topic for notifications.
    @return None
    """
    due_today, due_next_4, due_after_4 = [], [], []

    rules = [
        (0, 0, Colors.RED_BRIGHT, due_today),
        (1, 4, [Colors.YELLOW_BRIGHT, Colors.YELLOW_MEDIUM, Colors.YELLOW_DARK], due_next_4),
        (5, 7, Colors.GREEN_BRIGHT, due_after_4),
        (8, 14, Colors.GREEN_MEDIUM, due_after_4),
        (15, float("inf"), Colors.GREEN_DARK, due_after_4),
    ]

    submitted_color = Colors.GREEN_BRIGHT
    show_submitted = lambda s: f"{submitted_color} (Submitted){Colors.RESET}" if s else ""
    show_extended = lambda e: f"{submitted_color} (Extended){Colors.RESET}" if e else ""

    for assignment in sorted(assignments, key=lambda a: a.days_left):
        days_left = assignment.days_left
        display_date = format_day_month(assignment.deadline_date)

        for start, end, color, target in rules:
            if start <= days_left <= end:
                if isinstance(color, list):
                    color = color[min(days_left - start, len(color) - 1)]

                suffix = f" ({days_left} Days Left)" if days_left > 0 else ""
                target.append(
                    f"{color}A{assignment.number} {assignment.subject}"
                    f"{' - ' + display_date if days_left > 0 else ''}"
                    f"{suffix}{show_submitted(assignment.submitted)}{show_extended(assignment.extended)}{Colors.RESET}"
                )

    sections = [
        ("=== Due Today ===", due_today),
        ("=== Due Within the Next 4 Days ===", due_next_4),
        ("=== Due After 4 Days ===", due_after_4),
    ]

    for title, items in sections:
        if items:
            print(title)
            for line in items:
                print(line)
            print()

    if KDE_device or ntfy_server:
        notifications = build_deadline_notifications(assignments)

        if KDE_device:
            for notification in notifications:
                subprocess.run(["kdeconnect-cli", "--device", KDE_device, "--ping-msg", notification.message])

        send_deadline_notifications(ntfy_server, notifications)

if __name__ == "__main__":
    try:
        if DOWNLOAD_DIR == "" or USER_DATA_DIR == "":
            print("Error: One or more required environment variables are not set.")
            sys.exit(1)

        args = parse_args()
        context = None

        with sync_playwright() as p:
            try:
                context = start_browser(p, USER_DATA_DIR, headless=not (args.login or args.debug))
                page = get_page(context)
                check_and_login(context, page, args.debug, args.login)
                assignments = fetch_assignments(page, DOWNLOAD_DIR if args.download_assignments else None)
                close_browser(context)
            except Exception as e:
                handle_script_error(e, context, "checkAssignments")
                sys.exit(1)

        clear_terminal()

        if args.whatsapp:
            display_whatsapp_formatted_deadlines(assignments)
        else:
            display_deadlines(assignments, args.kde, args.ntfy)

        if args.download_assignments:
            cleanup_old_files(DOWNLOAD_DIR, [a.file_path for a in assignments if a.file_path], args.debug)

        if CHECK_UPDATES:
            check_for_updates()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)