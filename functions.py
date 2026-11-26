"""
@brief Shared configuration and helpers used by all the Bahria University automation scripts.

Anything that more than one script does (logging in, opening the LMS, scraping assignments
or attendance, sending notifications, launching the browser, ...) lives here so a fix only
has to be made once.
"""
from playwright.sync_api import Playwright, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError
from datetime import datetime, date
from typing import NamedTuple, Optional
from dotenv import load_dotenv
from time import sleep
import subprocess
import platform
import requests
import json
import glob
import os

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()

def _int_env(name: str, default: int) -> int:
    """
    @brief Reads an integer environment variable, falling back to the default if unset or blank.
    @param name The environment variable name.
    @param default The value to use if the variable is unset or blank.
    @return The integer value.
    """
    value = os.getenv(name, "").strip()
    return int(value) if value else default

ENROLLMENT_NUMBER = os.getenv("ENROLLMENT_NUMBER", "")
PASSWORD = os.getenv("PASSWORD", "")
USER_DATA_DIR = os.getenv("USER_DATA_DIR", "")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "")
NTFY_SERVER = os.getenv("NTFY_SERVER", "")
NOTIFICATION_LEVEL = _int_env("NOTIFICATION_LEVEL", 0)
NOTIFY_EXTENDED = _int_env("NOTIFY_EXTENDED", 1)
# Position of the campus in the CMS login page's institute dropdown ("Select" is 0, Islamabad E-8 is 5)
INSTITUTION = _int_env("INSTITUTION", 5)
CHECK_UPDATES = _int_env("CHECK_UPDATES", 1)
DOWNLOAD_ASSIGNMENTS = _int_env("DOWNLOAD_ASSIGNMENTS", 0)

# Survey demographics (fillSurveys.py)
DISABLED = _int_env("DISABLED", 0)
GENDER = _int_env("GENDER", 0)
AGE = _int_env("AGE", 0)
ON_CAMPUS = _int_env("ON_CAMPUS", 1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

CMS_LOGIN_URL = "https://cms.bahria.edu.pk/Logins/Student/Login.aspx"
CMS_LOGOFF_URL = "https://cms.bahria.edu.pk/Sys/Student/Logoff.aspx"
CMS_GO_TO_LMS_URL = "https://cms.bahria.edu.pk/Sys/Common/GoToLMS.aspx"
CMS_ATTENDANCE_URL = "https://cms.bahria.edu.pk/Sys/Student/ClassAttendance/StudentWiseAttendance.aspx"
CMS_SURVEYS_URL = "https://cms.bahria.edu.pk/Sys/Student/QualityAssurance/QualityAssuranceSurveys.aspx"
LMS_ASSIGNMENTS_URL = "https://lms.bahria.edu.pk/Student/Assignments.php"
LMS_SIGNOUT_URL = "https://lms.bahria.edu.pk/Student/includes/studentprocess.php?s=signout"
VERSION_URL = "https://raw.githubusercontent.com/Mujtaba0150/Bahria-University-Automation/master/version.txt"

DEFAULT_TIMEOUT = 60000

# ---------------------------------------------------------------------------
# General utilities
# ---------------------------------------------------------------------------

def clear_terminal():
    """
    @brief Clears the terminal/console screen based on the operating system.
    @return None
    """
    command = "cls" if platform.system() == "Windows" else "clear"
    subprocess.run(command, shell=True)

def check_for_updates():
    """
    @brief Checks if a new version of the application is available on GitHub.
    @return None
    """
    with open(os.path.join(SCRIPT_DIR, "version.txt"), "r") as f:
        local_version = f.readline().strip()

    try:
        response = requests.get(VERSION_URL, timeout=5)
        response.raise_for_status()
        remote_version = response.text.strip()

        if local_version != remote_version:
            print(f"A new version ({remote_version}) is available! You are using version {local_version}. Please update to the latest version.")
            print("Visit https://github.com/Mujtaba0150/Bahria-University-Automation to download the latest version or use git to update.")
    except requests.RequestException:
        print("Could not check for updates. Please check your internet connection.")

def format_number(n: float) -> str:
    """
    @brief Formats a number to 2 decimal places, removing trailing zeros and decimal points.
    @param n The number to format.
    @return Formatted string representation of the number.
    """
    return f"{n:.2f}".rstrip('0').rstrip('.')

def format_day_month(d: date) -> str:
    """
    @brief Formats a date as "7 November" (no leading zero) on every OS.
    @param d The date to format.
    @return The formatted date string.
    """
    return f"{d.day} {d.strftime('%B')}"

# ---------------------------------------------------------------------------
# Browser
# ---------------------------------------------------------------------------

BROWSER_ARGS = [
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
    "--blink-settings=imagesEnabled=false",
    "--disable-component-update",
    "--disable-background-networking",
    "--disable-sync",
    "--disable-lazy-image-loading",
    "--disable-features=Translate,BackForwardCache,RendererCodeIntegrity,IsolateOrigins,site-per-process",
    "--disable-animations",
    "--mute-audio",
]

def _block_unneeded_resources(route):
    """
    @brief Route handler that skips images, styles, fonts, analytics and non-CMS scripts to speed up page loads.
    @param route The Playwright route to continue or abort.
    @return None
    """
    request = route.request
    if (request.resource_type in ["image", "media", "font", "stylesheet"]
            or (request.resource_type == "script" and not request.url.startswith("https://cms.bahria.edu.pk/"))
            or "google-analytics" in request.url
            or "fontawesome" in request.url):
        route.abort()
    else:
        route.continue_()

def start_browser(p: Playwright, user_data_dir: Optional[str] = None, headless: bool = True, block_resources: bool = True) -> BrowserContext:
    """
    @brief Launches Chromium with optimized settings.
    @param p The Playwright instance from sync_playwright().
    @param user_data_dir Profile directory for a persistent session (keeps you logged in). None for a fresh, throwaway session.
    @param headless Whether to hide the browser window.
    @param block_resources Whether to skip images, styles, fonts and non-CMS scripts.
    @return The BrowserContext to work in.
    """
    if user_data_dir:
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=headless,
            no_viewport=True,
            args=BROWSER_ARGS + [
                f"--disk-cache-dir={user_data_dir}/playwrightCache",
                "--disk-cache-size=1073741824",
            ],
        )
    else:
        browser = p.chromium.launch(headless=headless, args=BROWSER_ARGS)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})

    if block_resources:
        context.route("**/*", _block_unneeded_resources)

    return context

def get_page(context: BrowserContext) -> Page:
    """
    @brief Returns the context's first tab (creating one if needed) with the default timeout applied.
    @param context The BrowserContext from start_browser().
    @return The Page to work with.
    """
    page = context.pages[0] if context.pages else context.new_page()
    page.set_default_timeout(DEFAULT_TIMEOUT)
    return page

def close_browser(context: BrowserContext):
    """
    @brief Closes the context and, for non-persistent sessions, the browser behind it.
    @param context The BrowserContext from start_browser().
    @return None
    """
    browser = context.browser
    context.close()
    if browser:
        browser.close()

def save_debug_info(context: Optional[BrowserContext], script_name: str):
    """
    @brief Saves the current page's HTML and a screenshot to error_logs/ for debugging.
    @param context The BrowserContext (may be None if the browser never started).
    @param script_name Prefix for the saved files.
    @return None
    """
    if not context or not context.pages:
        return

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    error_dir = os.path.join(SCRIPT_DIR, "error_logs")
    os.makedirs(error_dir, exist_ok=True)

    html_file = os.path.join(error_dir, f"{script_name}_error_{timestamp}.html")
    screenshot_file = os.path.join(error_dir, f"{script_name}_error_{timestamp}.png")

    try:
        page = context.pages[0]
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(page.content())
        page.screenshot(path=screenshot_file, full_page=True)
        print(f"Saved debug HTML to: {html_file}")
        print(f"Saved screenshot to: {screenshot_file}")
    except Exception as inner_e:
        print(f"Failed to save debug info: {inner_e}")

def handle_script_error(e: Exception, context: Optional[BrowserContext], script_name: str):
    """
    @brief Prints a friendly message for an error raised while automating, saving debug info when useful.
    Must be called while Playwright is still running (inside the sync_playwright() block).
    @param e The exception that was raised.
    @param context The BrowserContext (may be None).
    @param script_name Prefix for any saved debug files.
    @return None
    """
    error_message = str(e)

    if "ERR_INTERNET_DISCONNECTED" in error_message:
        print("No internet connection. Please check your connection and try again.")
        return

    if isinstance(e, PlaywrightTimeoutError):
        print("Operation timed out. The LMS or CMS might be down or unresponsive.")
    print(f"A playwright error occurred: {e}")
    save_debug_info(context, script_name)

# ---------------------------------------------------------------------------
# CMS / LMS login
# ---------------------------------------------------------------------------

def select_institution(page: Page, institution: int = INSTITUTION):
    """
    @brief Picks the campus in the CMS login page's institute dropdown.
    @param page The Playwright page on the CMS login page.
    @param institution Position of the campus in the dropdown (see INSTITUTION).
    @return None
    """
    page.select_option("#BodyPH_ddlInstituteID", index=institution)

def wait_for_login(page: Page, timeout: Optional[float] = None):
    """
    @brief Waits until the login postback has finished and the browser has left the login page.
    @param page The Playwright page object.
    @param timeout Optional timeout in milliseconds (defaults to the page's default timeout).
    @return None
    """
    page.wait_for_url(lambda url: "Login.aspx" not in url, wait_until="commit", timeout=timeout)

def login_to_cms(page: Page, enrollment_number: str = ENROLLMENT_NUMBER, password: str = PASSWORD):
    """
    @brief Logs into the CMS with the given credentials.
    @param page The Playwright page object.
    @param enrollment_number The student's enrollment number.
    @param password The student's CMS password.
    @return None
    """
    if "Login.aspx" not in page.url:
        page.goto(CMS_LOGIN_URL)
    page.fill("#BodyPH_tbEnrollment", enrollment_number)
    page.fill("#BodyPH_tbPassword", password)
    select_institution(page)
    page.click("#BodyPH_btnLogin")
    wait_for_login(page)
    print(f"Logged in as {enrollment_number}")

def is_survey_pending(page: Page) -> bool:
    """
    @brief Checks whether the CMS redirected to the mandatory Quality Assurance survey page.
    @param page The Playwright page object.
    @return True if a survey has to be completed first.
    """
    return "QualityAssuranceSurveys.aspx" in page.url

def ensure_cms_login(context: BrowserContext, page: Page, target_url: str, debug_mode: bool = False):
    """
    @brief Opens a CMS page, logging in (or switching accounts) first if needed.
    If a Quality Assurance survey is pending, the CMS redirects to it instead; check is_survey_pending() afterwards.
    @param context The BrowserContext (used to persist cookies after logging in).
    @param page The Playwright page object.
    @param target_url The CMS page to end up on.
    @param debug_mode Boolean flag to enable debug output.
    @return None
    """
    page.goto(target_url)

    if "Login.aspx" in page.url:
        if debug_mode:
            print("Login required. Logging in...")
        login_to_cms(page)
        persist_cookies(context, debug_mode)
        if not is_survey_pending(page):
            page.goto(target_url)
        return

    logged_in_enrollment_number = page.locator("#ProfileInfo_lblUsername").text_content().strip()
    if ENROLLMENT_NUMBER not in logged_in_enrollment_number:
        if debug_mode:
            print("Logged in with a different account. Logging out...")
        page.goto(CMS_LOGOFF_URL, wait_until="commit")
        ensure_cms_login(context, page, target_url, debug_mode)

def go_to_lms(page: Page):
    """
    @brief Opens the LMS through CMS's GoToLMS.aspx handoff page.
    GoToLMS.aspx returns a page whose script redirects to lms.bahria.edu.pk, where the
    LMS session cookie is issued. page.goto() only waits for GoToLMS.aspx itself, so any
    navigation started right after it aborts the JS redirect. Instead, we only wait for
    the GoToLMS.aspx response to commit, then wait for the browser to actually land on LMS.
    @param page The Playwright page object (already logged into CMS).
    @return None
    """
    try:
        page.goto(CMS_GO_TO_LMS_URL, wait_until="commit")
    except Exception as e:
        # The JS redirect can fire before goto() resolves and get reported as an
        # interrupted/aborted navigation. That's expected; anything else is a real error.
        if "interrupted by another navigation" not in str(e) and "ERR_ABORTED" not in str(e):
            raise

    page.wait_for_url("https://lms.bahria.edu.pk/**", wait_until="domcontentloaded")
    print("Opened LMS")

def persist_cookies(context: BrowserContext, debug_mode: bool = False):
    """
    @brief Makes the CMS and LMS session cookies persistent for one year so the session survives restarts.
    @param context The BrowserContext containing the cookies.
    @param debug_mode Boolean flag to enable debug output.
    @return None
    """
    for cookie in context.cookies():
        if cookie["name"] in ["cms", "PHPSESSID"]:
            cookie["expires"] = datetime.now().timestamp() + 31536000
            context.add_cookies([cookie])
            if debug_mode:
                print(f"Made {cookie['name']} cookie persistent.")

# ---------------------------------------------------------------------------
# Assignments
# ---------------------------------------------------------------------------

class Assignment(NamedTuple):
    number: str
    subject: str
    deadline: str           # As shown on the LMS, e.g. "22 November 2026"
    submitted: bool
    extended: bool
    file_path: Optional[str]

    @property
    def deadline_date(self) -> date:
        return datetime.strptime(self.deadline, "%d %B %Y").date()

    @property
    def days_left(self) -> int:
        return (self.deadline_date - datetime.today().date()).days

def download_assignment_file(page: Page, download_dir: str, subject_name: str, assignment_name: str, deadline_date: str, assignment_link: str) -> str:
    """
    @brief Downloads an assignment file into a subject-specific directory, skipping it if already downloaded.
    @param page The Playwright page object to interact with.
    @param download_dir The root directory for downloaded assignments.
    @param subject_name The name of the subject for the assignment.
    @param assignment_name The name of the assignment.
    @param deadline_date The deadline date formatted as string.
    @param assignment_link The URL link to the assignment file.
    @return The path of the downloaded (or previously downloaded) file.
    """
    subject_dir = os.path.join(download_dir, subject_name)
    os.makedirs(subject_dir, exist_ok=True)
    file_base = f"{assignment_name} - {deadline_date}"

    existing_files = glob.glob(os.path.join(glob.escape(subject_dir), f"{glob.escape(file_base)}.*"))
    if existing_files:
        return existing_files[0]

    with page.expect_download() as download_info:
        page.evaluate("link => window.location.href = link", assignment_link)

    download = download_info.value
    _, file_ext = os.path.splitext(download.suggested_filename)
    final_path = os.path.join(subject_dir, f"{file_base}{file_ext}")
    download.save_as(final_path)

    return final_path

def fetch_assignments(page: Page, download_dir: Optional[str] = None) -> list[Assignment]:
    """
    @brief Fetches all active (submittable or submitted-but-deletable) assignments from the LMS.
    @param page The Playwright page object (already logged into the LMS).
    @param download_dir If given, assignment files are downloaded here.
    @return List of Assignment entries.
    """
    assignments = []

    # Navigate to Assignments page if not already there
    if "Assignments.php" not in page.url:
        page.goto(LMS_ASSIGNMENTS_URL, wait_until="commit")
    page.wait_for_selector("#courseId", state="attached")

    # Extract subject names directly from the dropdown
    subjects = page.evaluate("""() => {
        return Array.from(document.querySelectorAll('#courseId option'))
            .filter(opt => opt.value !== "")
            .map(opt => opt.innerText.trim());
    }""")

    for subject in subjects:
        # Select the subject by name. Option values are one-time tokens that change on every
        # page load, and selecting a subject reloads the page, so stored IDs go stale.
        with page.expect_navigation(wait_until="domcontentloaded"):
            page.select_option("#courseId", label=subject)

        # Wait for the table to refresh for the specific subject
        try:
            page.wait_for_selector("table.table-hover tbody tr:not(:first-child)", timeout=5000)
        except PlaywrightTimeoutError:
            # If no assignments are found for this subject, skip to next
            continue

        # Extract table data using browser-side execution for speed and reliability
        table_data = page.evaluate("""() => {
            const rows = Array.from(document.querySelectorAll("table.table-hover tbody tr")).slice(1);
            return rows.map(row => {
                const cells = row.querySelectorAll("td");
                if (cells.length < 8) return null;

                const deadlineSmall = cells[7].querySelector("small");
                const downloadLink = cells[2].querySelector("a");
                return {
                    action: cells[6].innerText,
                    assignment_number: cells[0].innerText.trim(),
                    assignment_name: cells[1].innerText.trim(),
                    deadline_text: deadlineSmall ? deadlineSmall.innerText : "",
                    deadline_title: deadlineSmall ? deadlineSmall.getAttribute("title") || "" : "",
                    download_url: downloadLink ? downloadLink.getAttribute("href") : ""
                };
            }).filter(item => item !== null);
        }""")

        for item in table_data:
            # Check if assignment is active (Submit or Delete present)
            if "Submit" not in item['action'] and "Delete" not in item['action']:
                continue

            # Extract date (ignoring time/days left suffix)
            deadline_date = item['deadline_text'].split('-')[0].strip()
            if not deadline_date:
                continue

            file_path = None
            if download_dir and item['download_url']:
                assignment_link = f"https://lms.bahria.edu.pk/Student/{item['download_url']}"
                file_path = download_assignment_file(page, download_dir, subject, item['assignment_name'], deadline_date, assignment_link)

            assignments.append(Assignment(
                number=item['assignment_number'],
                subject=subject,
                deadline=deadline_date,
                submitted="Delete" in item['action'],
                extended="Extended" in item['deadline_title'],
                file_path=file_path,
            ))

    return assignments

# ---------------------------------------------------------------------------
# Notifications (ntfy.sh)
# ---------------------------------------------------------------------------

class Notification(NamedTuple):
    message: str
    days_left: int
    priority: int
    file_path: Optional[str]

def send_notification(ntfy_server: str, title: str, message: str, priority: int, file_path: str = ""):
    """
    @brief Sends a notification via ntfy.sh, optionally with a file attached.
    @param ntfy_server The ntfy topic to send the notification to.
    @param title The title of the notification.
    @param message The message body of the notification.
    @param priority The priority level of the notification (1-5).
    @param file_path Optional file path to attach to the notification.
    @return None
    """
    if not ntfy_server:
        print("NTFY_SERVER is not set. Cannot send notification.")
        return

    if file_path:
        with open(file_path, 'rb') as f:
            requests.put(
                f"https://ntfy.sh/{ntfy_server}",
                data=f,
                headers={"Title": title, "Priority": str(priority), "File": os.path.basename(file_path)},
                params={"message": message},
                timeout=60,
            )
    else:
        requests.post(
            f"https://ntfy.sh/{ntfy_server}",
            data=message.encode('utf-8'),
            headers={"Title": title, "Priority": str(priority)},
            timeout=30,
        )

def fetch_cached_notifications(ntfy_server: str, messages: list[str]) -> list[dict]:
    """
    @brief Fetches previously sent ntfy notifications matching the given messages.
    @param ntfy_server The ntfy topic.
    @param messages List of notification message strings to look up.
    @return List of dicts with the cached notification id and message.
    """
    cached_notifications = []
    if not ntfy_server:
        return cached_notifications

    # ntfy.sh is unreliable over IPv6 from some networks, so force IPv4
    import urllib3.util.connection as urllib3Connection
    urllib3Connection.allowed_gai_family = lambda: __import__("socket").AF_INET

    for message in messages:
        response = requests.get(f"https://ntfy.sh/{ntfy_server}/json?poll=1&message={message}", timeout=30)

        for line in response.text.splitlines():
            if line.strip():
                data = json.loads(line)
                cached_notifications.append({
                    "id": data["id"],
                    "message": data["message"]
                })
    return cached_notifications

def delete_cached_notification(ntfy_server: str, message: str, cached_notifications: list[dict]):
    """
    @brief Deletes a previously sent ntfy notification so it isn't duplicated.
    @param ntfy_server The ntfy topic.
    @param message The notification message to delete.
    @param cached_notifications List returned by fetch_cached_notifications.
    @return None
    """
    for notification in cached_notifications:
        if notification["message"] == message.strip():
            requests.delete(f"https://ntfy.sh/{ntfy_server}/{notification['id']}", timeout=30)
            break

def build_deadline_notifications(assignments: list[Assignment], notification_level: int = NOTIFICATION_LEVEL, notify_extended: int = NOTIFY_EXTENDED) -> list[Notification]:
    """
    @brief Picks which assignments to notify about based on the notification level.
    @param assignments The assignments returned by fetch_assignments().
    @param notification_level 0 = due today, 1 = within 4 days, 2 = within 7 days, 3 = within 14 days, 4 = all.
    @param notify_extended Whether to also notify for submitted assignments whose deadline was extended.
    @return Notifications ordered furthest deadline first, so the most urgent one is sent last and shows on top.
    """
    level_to_max_days = {0: 0, 1: 4, 2: 7, 3: 14, 4: float("inf")}
    max_days_for_notification = level_to_max_days.get(notification_level, 0)

    notifications = []
    for assignment in sorted(assignments, key=lambda a: a.days_left, reverse=True):
        days_left = assignment.days_left
        if days_left > max_days_for_notification:
            continue
        if assignment.submitted and not (notify_extended and assignment.extended):
            continue

        message = f"{assignment.number}. {assignment.subject} - {format_day_month(assignment.deadline_date)} {'Submitted' if assignment.submitted else ''}"
        priority = 5 if days_left == 0 else 4 if days_left <= 4 else 3
        notifications.append(Notification(message, days_left, priority, assignment.file_path))

    return notifications

def send_deadline_notifications(ntfy_server: str, notifications: list[Notification], attach_files: bool = False):
    """
    @brief Sends deadline notifications via ntfy, replacing earlier copies of the same notification.
    @param ntfy_server The ntfy topic.
    @param notifications Notifications from build_deadline_notifications().
    @param attach_files Whether to attach downloaded assignment files.
    @return None
    """
    if not ntfy_server or not notifications:
        return

    cached_notifications = fetch_cached_notifications(ntfy_server, [n.message for n in notifications])

    for notification in notifications:
        if notification.days_left == 0:
            title = "Assignment Due Today"
        elif notification.days_left <= 14:
            title = f"Assignment Due in {notification.days_left} Days"
        else:
            title = "Upcoming Assignments"

        delete_cached_notification(ntfy_server, notification.message, cached_notifications)
        send_notification(ntfy_server, title, notification.message, notification.priority,
                          notification.file_path if attach_files and notification.file_path else "")
        sleep(0.1)  # Sleep to ensure notifications are sent in order

# ---------------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------------

class AttendanceRecord(NamedTuple):
    subject: str
    remaining: float    # Absences you can still afford (in classes); negative means over the limit
    maximum: int        # Total absences allowed (in classes)

def fetch_attendance(page: Page, debug_mode: bool = False) -> list[AttendanceRecord]:
    """
    @brief Scrapes the CMS attendance page and works out how many more absences each subject allows.
    @param page The Playwright page object (already logged into CMS).
    @param debug_mode Boolean flag to enable debug output.
    @return List of AttendanceRecord entries.
    """
    if "StudentWiseAttendance.aspx" not in page.url:
        page.goto(CMS_ATTENDANCE_URL)

    records = []
    rows = page.locator("#pageContent > div.container-fluid > div.table-responsive > table > tbody > tr").all()
    for row in rows:
        cells = row.locator("td").all()
        subject = cells[2].inner_text().strip()
        credits = int(cells[3].inner_text().strip())
        absences = float(cells[10].inner_text().strip())

        if debug_mode:
            print(f"Processing subject: {subject}, Credits: {credits}, Absences: {absences}")

        if credits == 0:
            credits = 1
            if debug_mode:
                print(f"Credits for {subject} was 0, setting to 1 to avoid division by zero.")

        if subject.split()[-1] == "Lab":
            max_absences = credits * 12
            remaining = (max_absences - absences) / (credits * 3)
            maximum = int(max_absences / (credits * 3))
        else:
            max_absences = credits * 4
            remaining = (max_absences - absences) / credits * 2
            maximum = int(max_absences / credits * 2)

        records.append(AttendanceRecord(subject, remaining, maximum))

    return records
