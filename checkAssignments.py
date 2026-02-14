from playwright.sync_api import sync_playwright, BrowserContext, Page, TimeoutError
from datetime import datetime
from dotenv import load_dotenv
from time import sleep
import platform
import subprocess
import requests
import argparse
import os
import glob

class Colors:
    RED_BRIGHT = "\x1b[38;2;255;0;0m"
    YELLOW_BRIGHT = "\x1b[38;2;251;255;0m"
    YELLOW_MEDIUM = "\x1b[38;2;255;241;49m"
    YELLOW_DARK = "\x1b[38;2;245;228;0m"
    GREEN_BRIGHT = "\x1b[38;2;25;189;25m"
    GREEN_MEDIUM = "\x1b[38;2;12;131;12m"
    GREEN_DARK = "\x1b[38;2;9;92;9m"
    RESET = "\033[0m"


subjectAbbreviations = {
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

load_dotenv()
download_dir = os.getenv("DOWNLOAD_DIR", "")
enrollment_number = os.getenv("ENROLLMENT_NUMBER", "")
password = os.getenv("PASSWORD", "")
data_dir = os.getenv("USER_DATA_DIR", "")
notification_level = int(os.getenv("NOTIFICATION_LEVEL", "0"))
notify_submitted = int(os.getenv("NOTIFY_SUBMITTED", "1"))
instituition = int(os.getenv("INSTITUTION", "6"))

def clean_text(text: str) -> str:
    return " ".join(text.split())

def clear_terminal():
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")

def parse_args():
    '''Parses command line arguments.'''
    parser = argparse.ArgumentParser()
    parser.add_argument("-k", "--kde", action="store", help="Send notifications via KDE Connect using Device ID")
    parser.add_argument("-N", "--ntfy", action="store", help="Send notifications via Ntfy using Server")
    parser.add_argument("-n", action="store_true", dest="check_assignments", help="Don't download assignments")
    parser.add_argument("-w", "--whatsapp", action="store_true", help="Format for WhatsApp Message")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode")
    return parser.parse_args()

def start_playwright(debug_mode: bool) -> BrowserContext:
    """Launches persistent browser and runs survey automation."""
    browser = p.chromium.launch_persistent_context(
        user_data_dir=data_dir,
        headless=not debug_mode,
        args=[
            "--window-size=1920,1080",
            "--disable-gpu",
            "--disable-software-rasterizer",
            "--disable-extensions",
            "--disable-infobars",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-logging",
            "--log-level=3",
            "--disable-features=Translate,BackForwardCache,RendererCodeIntegrity,IsolateOrigins,site-per-process",
            "--blink-settings=imagesEnabled=false",
            "--disable-animations",
            "--mute-audio"
        ]
    )

    return browser

def check_and_login(page, debug_mode: bool):
    '''Handles login and cookie persistence.'''
    page.goto("https://lms.bahria.edu.pk/Student/Assignments.php")
    if  ("https://lms.bahria.edu.pk/" in page.url):
        logged_in_enrollment_number = page.locator("body > div > header > nav > div > ul > li.dropdown.user.user-menu > ul > li.user-header > p").text_content().strip()
        if enrollment_number not in logged_in_enrollment_number:
            if debug_mode:
                print("Logged in with a different account. Logging out...")

            page.click("body > div > header > nav > div > ul > li.dropdown.user.user-menu")
            page.click("body > div > header > nav > div > ul > li.dropdown.user.user-menu.open > ul > li.user-footer > div.pull-right")
            if "Login.aspx" not in page.url:
                page.click("#AccountsNavbar > ul")
                page.click("#ProfileInfo_hlLogoff")
            check_and_login(page, debug_mode)
        else:
            print(f"Logged in as {enrollment_number}")

    else:
        page.goto("https://cms.bahria.edu.pk/Logins/Student/Login.aspx")
        if "Login.aspx" in page.url:
                page.goto("https://cms.bahria.edu.pk/Logins/Student/Login.aspx")
                page.fill("#BodyPH_tbEnrollment", enrollment_number)
                page.fill("#BodyPH_tbPassword", password)
                page.select_option("#BodyPH_ddlInstituteID", "1")
                page.click(f"#pageContent > div.container-fluid > div.row > div > div:nth-child({instituition})")

                print(f"Logged in as {enrollment_number}")
                lms_button = page.wait_for_selector("#sideMenuList > a:nth-child(16)")
                page.evaluate("el => el.removeAttribute('target')", lms_button)
                lms_button.click()

        elif ("QualityAssuranceSurveys.aspx" in page.url):
            print("Please complete the Quality Assurance Survey to proceed.")   
            run_qa_survey(page, debug_mode)

        persist_cookies(browser, debug_mode)

def persist_cookies(browser, debug_mode: bool):
    '''Makes CMS cookies persistent for a year.'''
    cookies = browser.cookies()
    for cookie in cookies:
        if cookie["name"] in ["cms", "PHPSESSID"]:
            cookie["expires"] = (datetime.now().timestamp() + 31536000)
            cookie["session"] = False
            browser.add_cookies([cookie])
            if debug_mode:
                print(f"Made {cookie['name']} cookie persistent.")

def run_qa_survey(page, debug_mode: bool):
            print("Do you want to run the script to fill the survey automatically? (y/n): ", end="")
            choice = input().strip().lower()
            if choice == 'y':
                survey_file_path = os.path.join(os.path.dirname(__file__), "fillSurvey.py")
                if os.path.exists(survey_file_path):
                    clear_terminal()
                    subprocess.run(["python", survey_file_path])
                else:
                    print("Survey automation script not found.")
                    exit(1)

def download_assignment_file(page, subject_name: str, assignment_name: str, deadline_date: str, assignment_link: str) -> str:
    '''Handles the downloading of an assignment file, creating directories if necessary, and returning the file pattern used to check for duplicates.'''
    if not os.path.exists(f"{download_dir}/{subject_name}"):
        os.makedirs(f"{download_dir}/{subject_name}")

    pattern = f"{download_dir}/{subject_name}/{assignment_name} - {deadline_date}.*"
    matching_files = glob.glob(pattern)

    if not matching_files:
        subject_dir = f"{download_dir}\\{subject_name}" if os.name == "nt" else f"{download_dir}/{subject_name}"
        file_base = f"{assignment_name} - {deadline_date}"

        with page.expect_download() as download_info:
            page.evaluate(f"window.location.href = '{assignment_link}'")

        download = download_info.value
        file_name = download.suggested_filename
        _, file_ext = os.path.splitext(file_name)
        final_path = os.path.join(subject_dir, f"{file_base}{file_ext}")
        download.save_as(final_path)

    return pattern

def cleanup_old_files(download_dir: str, patterns: list, debug_mode: bool):
    '''Delete all files and folders in download_dir that are not matched by any pattern.'''
    all_files = glob.glob(f"{download_dir}/**/*", recursive=True)
    keep_files = set()
    for pattern in patterns:
        keep_files.update(glob.glob(pattern))

    for path in all_files:
        if os.path.isdir(path):
            continue
        if path not in keep_files:
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

def fetch_assignments(page: Page, check_assignments:bool, debug_mode: bool) -> tuple[list, list]:
    '''Fetches assignments from the LMS and returns assignments with deadlines and patterns of downloaded files so that old assignment files can be cleaned up.'''
    deadlines = []
    patterns = []

    page.click("body > div > aside > section > ul > li:nth-child(5)")
    subjects_list = page.locator("#courseId option").all()
    subjects = [(i, clean_text(s.inner_text())) for i, s in enumerate(subjects_list)]
    for index, subject_name in subjects:
        page.select_option("#courseId", index=index)
        page.wait_for_selector("table.table-hover tbody tr")
        rows = page.locator("table.table-hover tbody tr").all()[1:]
        for row in rows:
            cells = row.locator("td").all()
            if len(cells) < 8:
                continue
            action_col = cells[6].text_content()
            if "Submit" in action_col or "Delete" in action_col: # pyright: ignore[reportOperatorIssue]
                assignment_number = cells[0].text_content().strip() # pyright: ignore[reportOptionalMemberAccess]
                assignment_name = cells[1].text_content().strip() # pyright: ignore[reportOptionalMemberAccess]
                deadline_date = cells[7].locator("small").first.text_content().split('-')[0].strip() # pyright: ignore[reportOptionalMemberAccess]
                
                if "Delete" in action_col: # pyright: ignore[reportOperatorIssue]
                    submitted = True
                else:
                    submitted = False

                if not check_assignments:
                    assignment_link = f"https://lms.bahria.edu.pk/Student/{cells[2].locator('a').get_attribute('href')}"
                    pattern = download_assignment_file(page, subject_name, assignment_name, deadline_date, assignment_link) # pyright: ignore[reportArgumentType]
                    patterns.append(pattern)
                
                if deadline_date:
                    deadlines.append((assignment_number, subject_name, deadline_date, submitted))

    return deadlines, patterns


def display_whatsapp_formatted_deadlines(deadlines: list):
    formattedDeadlines = []
    for subject, date, _ in deadlines:
        shortSubject = subjectAbbreviations.get(subject, subject)
        try:
            parsedDate = datetime.strptime(date, "%d %B %Y")
            day = parsedDate.day
            if 11 <= day <= 13:
                suffix = "th"
            else:
                suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
            formattedDate = f"{day}{suffix} {parsedDate.strftime('%b')}"
            formattedDeadlines.append((shortSubject, formattedDate, parsedDate))
        except ValueError:
            formattedDeadlines.append((shortSubject, date, None))

    formattedDeadlines.sort(key=lambda x: (x[2] is None, x[2]))

    for subject, formattedDate, _ in formattedDeadlines:
        print(f"{subject} - {formattedDate}")


def display_deadlines(deadlines: list, kdeDevice: str, ntfyServer: str):
    today = datetime.today().date()
    parsed_deadlines = []

    for assignment_number, subject, date_str, submitted in deadlines:
        deadline_date = datetime.strptime(date_str, "%d %B %Y").date()
        days_left = (deadline_date - today).days
        parsed_deadlines.append((assignment_number, subject, deadline_date, days_left, submitted))

    parsed_deadlines.sort(key=lambda x: x[1])

    dueToday, dueNext4, dueAfter4 = [], [], []

    rules = [
        (0, 0, Colors.RED_BRIGHT, dueToday, 5),
        (1, 4, [Colors.YELLOW_BRIGHT, Colors.YELLOW_MEDIUM, Colors.YELLOW_DARK], dueNext4, 4),
        (5, 7, Colors.GREEN_BRIGHT, dueAfter4, 3),
        (8, 14, Colors.GREEN_MEDIUM, dueAfter4, 3),
        (15, float("inf"), Colors.GREEN_DARK, dueAfter4, 2),
    ]

    level_to_max_days = {0: 0, 1: 4, 2: 7, 3: 14, 4: float("inf")}
    max_days_for_notification = level_to_max_days.get(notification_level, 0)

    notifications = []
    submitted_color = Colors.GREEN_BRIGHT
    show_submitted = lambda s: f"{submitted_color} (Submitted){Colors.RESET}" if s else ""

    for assignment_number, subject, deadline_date, days_left, submitted in parsed_deadlines:
        display_date = deadline_date.strftime("%#d %B") if os.name == "nt" else deadline_date.strftime("%-d %B")
        notification_message = f"{assignment_number} {subject} - {display_date} {'Submitted' if submitted else ''}"

        for start, end, color, target, priority in rules:
            if start <= days_left <= end:
                if isinstance(color, list):
                    color = color[min(days_left - start, len(color) - 1)]

                suffix = f" ({days_left} Days Left)" if days_left > 0 else ""
                colored = (
                    f"{color}A{assignment_number} {subject}"
                    f"{' - ' + display_date if days_left > 0 else ''}"
                    f"{suffix}{show_submitted(submitted)}{Colors.RESET}"
                )
                target.append(colored)

                if (kdeDevice or ntfyServer) and days_left <= max_days_for_notification:
                    if submitted and not notify_submitted:
                        break
                    notifications.append((notification_message, priority, submitted))
                break

    sections = [
        ("=== Due Today ===", dueToday),
        ("=== Due Within the Next 4 Days ===", dueNext4),
        ("=== Due After 4 Days ===", dueAfter4),
    ]

    for title, items in sections:
        if items:
            print(title)
            for line in items:
                print(line)
            print()

    for notification, priority, submitted in notifications:
        if kdeDevice and (not submitted or notify_submitted):
            subprocess.run(["kdeconnect-cli", "--device", kdeDevice, "--ping-msg", notification])

        if ntfyServer and (not submitted or notify_submitted):
            requests.post(
                f"https://ntfy.sh/{ntfyServer}",
                data=notification,
                headers={"Title": "Assignments Due Today", "Priority": str(priority)}
            )


if __name__ == "__main__":
    try:
        if download_dir == "" or enrollment_number == "" or password == "" or data_dir == "":
            print("Error: One or more required environment variables are not set.")
            exit(1)

        args = parse_args()
        browser = None

        try:
            with sync_playwright() as p:
                browser = start_playwright(args.debug)
                page = browser.pages[0]
                check_and_login(page, args.debug)
                deadlines, patterns = fetch_assignments(page, args.check_assignments, args.debug)
                browser.close()

        except Exception as e:
            error_message = str(e)

            if e == TimeoutError:
                print("Operation timed out. The LMS or CMS might be down or unresponsive.")
            
            elif ("ERR_INTERNET_DISCONNECTED" in error_message):
                print("No internet connection. Please check your connection and try again.")
            
            else:
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                errorDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "error_logs")
                os.makedirs(errorDir, exist_ok=True)

                htmlFile = f"{errorDir}/checkAssignments_error_{timestamp}.html"
                screenshotFile = f"{errorDir}/checkAssignments_error_{timestamp}.png"

                try:
                    print(f"A playwright error occurred: {e}")
                    if browser and browser.pages:
                        page = browser.pages[0]
                        with open(htmlFile, "w", encoding="utf-8") as f:
                            f.write(page.content())
                        page.screenshot(path=screenshotFile, full_page=True)
                        print(f"Saved debug HTML to: {htmlFile}")
                        print(f"Saved screenshot to: {screenshotFile}")
                        browser.close()
                except Exception as inner_e:
                    print(f"Failed to save debug info: {inner_e}")
            exit(1)

        clear_terminal()

        if args.whatsapp:
            display_whatsapp_formatted_deadlines(deadlines)
        else:
            display_deadlines(deadlines, args.kde, args.ntfy)
        cleanup_old_files(download_dir, patterns, args.debug)
    
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        exit(1)