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

load_dotenv()
download_dir = os.getenv("DOWNLOAD_DIR", "")
enrollment_number = os.getenv("ENROLLMENT_NUMBER", "")
password = os.getenv("PASSWORD", "")
data_dir = os.getenv("USER_DATA_DIR", "")
notification_level = int(os.getenv("NOTIFICATION_LEVEL", "0"))
notify_extended = int(os.getenv("NOTIFY_EXTENDED", "1"))
instituition = int(os.getenv("INSTITUTION", "6"))
check_updates = int(os.getenv("CHECK_UPDATES", "1"))

def clean_text(text: str) -> str:
    """
    @brief Removes extra whitespace from text by collapsing multiple spaces into single spaces.
    @param text The input string to clean.
    @return String with normalized whitespace.
    """
    return " ".join(text.split())

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
    with open(os.path.join(os.path.dirname(__file__), "version.txt"), "r") as f:
        local_version = f.readline().strip()
        f.close()

    try:
        url = "https://raw.githubusercontent.com/Mujtaba0150/Bahria-University-Automation/master/version.txt"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        remote_version = response.text.strip()

        if local_version != remote_version:
            print(f"A new version ({remote_version}) is available! You are using version {local_version}. Please update to the latest version.")
            print("Visit https://github.com/Mujtaba0150/Bahria-University-Automation to download the latest version or use git to update.")
    except requests.RequestException:
        print("Could not check for updates. Please check your internet connection.")

def parse_args():
    """
    @brief Parses command-line arguments for the assignment checker.
    @return Parsed arguments object with kde, ntfy, download_assignments, whatsapp, and debug options.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-k", "--kde", action="store", help="Send notifications via KDE Connect using Device ID")
    parser.add_argument("-N", "--ntfy", action="store", help="Send notifications via Ntfy using Server")
    parser.add_argument("-n", action="store_false", dest="download_assignments", help="Don't download assignments")
    parser.add_argument("-w", "--whatsapp", action="store_true", help="Format for WhatsApp Message")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode")
    return parser.parse_args()

def start_playwright(debug_mode: bool) -> BrowserContext:
    """
    @brief Launches a persistent Chromium browser with optimized settings.
    @param debug_mode Boolean flag to launch browser in debug mode (non-headless).
    @return BrowserContext object representing the persistent browser context.
    """
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
            "--blink-settings=imagesEnabled=false",
            "--disable-component-update",
            "--disable-background-networking",
            "--disable-sync",
            "--disable-lazy-image-loading",
            "--disable-blink-features=AutomationControlled",
            "--disable-logging",
            "--log-level=3",
            f"--disk-cache-dir={data_dir}/playwrightCache",
            "--disk-cache-size=1073741824",
            "--disable-features=Translate,RendererCodeIntegrity,IsolateOrigins,site-per-process",
            "--disable-animations",
            "--mute-audio"
        ]
    )
    
    browser.route("**/*", lambda route: 
        route.abort() if route.request.resource_type in ["image", "media", "font", "stylesheet"]
        or route.request.resource_type == "script" and not (route.request.url.startswith("https://cms.bahria.edu.pk/"))
        or "google-analytics" in route.request.url 
        or "fontawesome" in route.request.url
        else route.continue_()
    )
    
    return browser

def check_and_login(page, debug_mode: bool):
    """
    @brief Handles user login and ensures proper authentication before accessing assignments.
    @param page The Playwright page object to interact with.
    @param debug_mode Boolean flag to enable debug output.
    @return None
    """
    page.goto("https://lms.bahria.edu.pk/Student/Assignments.php", wait_until="commit")
    if  ("https://lms.bahria.edu.pk/" in page.url):
        logged_in_enrollment_number = page.locator("body > div > header > nav > div > ul > li.dropdown.user.user-menu > ul > li.user-header > p").text_content().strip()
        if enrollment_number not in logged_in_enrollment_number:
            if debug_mode:
                print("Logged in with a different account. Logging out...")

            page.goto("https://lms.bahria.edu.pk/Student/includes/studentprocess.php?s=signout", wait_until="commit")
            page.goto("https://cms.bahria.edu.pk/Sys/Student/Logoff.aspx", wait_until="commit")
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
                page.click("#BodyPH_btnLogin")
                print(f"Logged in as {enrollment_number}")
                lms_button = page.wait_for_selector("#sideMenuList > a:nth-child(16)")
                page.evaluate("el => el.removeAttribute('target')", lms_button)
                lms_button.click()

        elif ("QualityAssuranceSurveys.aspx" in page.url):
            print("Please complete the Quality Assurance Survey to proceed.")   
            run_qa_survey(page, debug_mode)
        
        else:
            print(f"Logged in as {enrollment_number}")
            lms_button = page.wait_for_selector("#sideMenuList > a:nth-child(16)")
            page.evaluate("el => el.removeAttribute('target')", lms_button)
            lms_button.click()

        persist_cookies(browser, debug_mode)

def persist_cookies(browser, debug_mode: bool):
    """
    @brief Makes CMS cookies persistent for one year to maintain session across restarts.
    @param browser The BrowserContext object containing the cookies.
    @param debug_mode Boolean flag to enable debug output.
    @return None
    """
    cookies = browser.cookies()
    for cookie in cookies:
        if cookie["name"] in ["cms", "PHPSESSID"]:
            cookie["expires"] = (datetime.now().timestamp() + 31536000)
            cookie["session"] = False
            browser.add_cookies([cookie])
            if debug_mode:
                print(f"Made {cookie['name']} cookie persistent.")

def run_qa_survey(page, debug_mode: bool):
    """
    @brief Prompts user to run automated survey filling script.
    @param page The Playwright page object.
    @param debug_mode Boolean flag to enable debug output.
    @return None
    """
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
    """
    @brief Downloads an assignment file and saves it in a subject-specific directory.
    @param page The Playwright page object to interact with.
    @param subject_name the name of the subject for the assignment.
    @param assignment_name The name of the assignment.
    @param deadline_date The deadline date formatted as string.
    @param assignment_link The URL link to the assignment file.
    @return File pattern used to identify downloaded files for cleanup.
    """
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
    """
    @brief Deletes old assignment files not matching current download patterns.
    @param download_dir The root directory containing downloaded assignments.
    @param patterns List of file patterns to keep during cleanup.
    @param debug_mode Boolean flag to enable debug output.
    @return None
    """
    all_files = glob.glob(f"{download_dir}/**/*", recursive=True)
    keep_files = set()
    
    for pattern in patterns:
        keep_files.update(glob.glob(pattern))
        
    if platform.system() == "Windows":
        download_dir = download_dir.replace("/", "\\")
        keep_files = {f.replace("/", "\\") for f in keep_files}
    
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

def send_notification(title, message: str, priority: int, ntfy_server: str):
    """
    @brief Sends a notification via ntfy.sh service.
    @param title The title of the notification.
    @param message The message body of the notification.
    @param priority The priority level of the notification (1-5).
    @param ntfy_server The ntfy server name/topic to send the notification to.
    @return None
    """
    if ntfy_server:
        requests.put(
            f"https://ntfy.sh/{ntfy_server}",
            data=message,
            headers={"Title": title, "Priority": str(priority)}
        )
    else:
        print("ntfy_server is not set. Cannot send notification.")

def fetch_assignments(page: Page, download_assignments: bool, debug_mode: bool) -> tuple[list, list]:
    deadlines = []
    patterns = []
    if "Assignments.php" not in page.url:
        page.goto("https://lms.bahria.edu.pk/Student/Assignments.php", wait_until="networkidle")

    # Extract courses and values
    courses = page.evaluate("""() => {
        return Array.from(document.querySelectorAll('#courseId option'))
            .filter(opt => opt.value !== "")
            .map(opt => ({ id: opt.value, name: opt.innerText.trim() }));
    }""")

    for course in courses:
        page.select_option("#courseId", value=course['id'])
        
        page.wait_for_selector("table.table-hover tbody tr:not(:first-child)", timeout=5000)

        table_data = page.evaluate("""() => {
            const rows = Array.from(document.querySelectorAll("table.table-hover tbody tr")).slice(1);
            return rows.map(row => {
                const cells = row.querySelectorAll("td");
                if (cells.length < 8) return null;
                return {
                    action: cells[6].innerText,
                    assignment_number: cells[0].innerText.trim(),
                    assignment_name: cells[1].innerText.trim(),
                    deadline_text: cells[7].querySelector("small")?.innerText || "",
                    deadline_title: cells[7].querySelector("small")?.getAttribute("title") || "",
                    download_url: cells[2].querySelector("a")?.getAttribute("href") || ""
                };
            }).filter(item => item !== null);
        }""")

        for item in table_data:
            if "Submit" in item['action'] or "Delete" in item['action']:
                deadline_date = item['deadline_text'].split('-')[0].strip()
                if not deadline_date: continue

                if download_assignments and item['download_url']:
                    link = f"https://lms.bahria.edu.pk/Student/{item['download_url']}"
                    patterns.append(download_assignment_file(page, course['name'], item['assignment_name'], deadline_date, link))
                
                deadlines.append((
                    item['assignment_number'], 
                    course['name'], 
                    deadline_date, 
                    "Delete" in item['action'], 
                    "Extended" in item['deadline_title']
                ))

    return deadlines, patterns

def display_whatsapp_formatted_deadlines(deadlines: list):
    """
    @brief Formats and displays assignment deadlines in WhatsApp-friendly format.
    @param deadlines List of tuples containing deadline information.
    @return None
    """
    formatted_deadlines = []
    for subject, date, _ in deadlines:
        short_subject = subject_abbreviations.get(subject, subject)
        try:
            parsed_date = datetime.strptime(date, "%d %B %Y")
            day = parsed_date.day
            if 11 <= day <= 13:
                suffix = "th"
            else:
                suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
            formatted_date = f"{day}{suffix} {parsed_date.strftime('%b')}"
            formatted_deadlines.append((short_subject, formatted_date, parsed_date))
        except ValueError:
            formatted_deadlines.append((short_subject, date, None))

    formatted_deadlines.sort(key=lambda x: (x[2] is None, x[2]))

    for subject, formatted_date, _ in formatted_deadlines:
        print(f"{subject} - {formatted_date}")

def display_deadlines(deadlines: list, KDE_device: str, ntfy_server: str):
    """
    @brief Displays and processes assignment deadlines with color coding and notifications.
    @param deadlines List of tuples containing deadline information.
    @param KDE_device KDE Connect device ID for notifications.
    @param ntfy_server Ntfy service name for notifications.
    @return None
    """
    today = datetime.today().date()
    parsed_deadlines = []

    for assignment_number, subject, date_str, submitted, extended in deadlines:
        deadline_date = datetime.strptime(date_str, "%d %B %Y").date()
        days_left = (deadline_date - today).days
        parsed_deadlines.append((assignment_number, subject, deadline_date, days_left, submitted, extended))

    parsed_deadlines.sort(key=lambda x: x[3])

    due_today, due_next_4, due_after_4 = [], [], []

    rules = [
        (0, 0, Colors.RED_BRIGHT, due_today, 5),
        (1, 4, [Colors.YELLOW_BRIGHT, Colors.YELLOW_MEDIUM, Colors.YELLOW_DARK], due_next_4, 4),
        (5, 7, Colors.GREEN_BRIGHT, due_after_4, 3),
        (8, 14, Colors.GREEN_MEDIUM, due_after_4, 3),
        (15, float("inf"), Colors.GREEN_DARK, due_after_4, 2),
    ]

    level_to_max_days = {0: 0, 1: 4, 2: 7, 3: 14, 4: float("inf")}
    max_days_for_notification = level_to_max_days.get(notification_level, 0)

    notifications = []
    submitted_color = Colors.GREEN_BRIGHT
    show_submitted = lambda s: f"{submitted_color} (Submitted){Colors.RESET}" if s else ""
    show_extended = lambda e: f"{submitted_color} (Extended){Colors.RESET}" if e else ""

    for assignment_number, subject, deadline_date, days_left, submitted, extended in parsed_deadlines:
        display_date = deadline_date.strftime("%#d %B") if os.name == "nt" else deadline_date.strftime("%-d %B")
        notification_message = f"{assignment_number}. {subject} - {display_date} {'Submitted' if submitted else ''}"

        for start, end, color, target, priority in rules:
            if start <= days_left <= end:
                if isinstance(color, list):
                    color = color[min(days_left - start, len(color) - 1)]

                suffix = f" ({days_left} Days Left)" if days_left > 0 else ""
                colored = (
                    f"{color}A{assignment_number} {subject}"
                    f"{' - ' + display_date if days_left > 0 else ''}"
                    f"{suffix}{show_submitted(submitted)}{show_extended(extended)}{Colors.RESET}"
                )
                target.append(colored)

                if (KDE_device or ntfy_server) and (days_left <= max_days_for_notification) and not submitted or (notify_extended and extended):
                    notifications.append((notification_message, days_left, priority, submitted, extended))

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

    if ntfy_server or KDE_device:
        for notification, days_left, priority, submitted, extended in notifications:
            if KDE_device and (not submitted or (notify_extended and extended)):
                subprocess.run(["kdeconnect-cli", "--device", KDE_device, "--ping-msg", notification])

            if ntfy_server and (not submitted or (notify_extended and extended)):
                if days_left == 0:
                    send_notification("Assignment Due Today", notification, priority, ntfy_server)
                elif days_left <= 4:
                    send_notification("Assignment Due in Next 4 Days", notification, priority, ntfy_server)
                elif days_left <= 7:
                    send_notification("Assignment Due in Next 7 Days", notification, priority, ntfy_server)
                elif days_left <= 14:
                    send_notification("Assignment Due in Next 14 Days", notification, priority, ntfy_server)
                else:
                    send_notification("Upcoming Assignments", notification, priority, ntfy_server)

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
                page.set_default_timeout(60000)
                check_and_login(page, args.debug)
                deadlines, patterns = fetch_assignments(page, args.download_assignments, args.debug)
                browser.close()

        except Exception as e:
            error_message = str(e)

            if e == TimeoutError:
                print("Operation timed out. The LMS or CMS might be down or unresponsive.")
            
            elif ("ERR_INTERNET_DISCONNECTED" in error_message):
                print("No internet connection. Please check your connection and try again.")
            
            else:
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                error_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "error_logs")
                os.makedirs(error_dir, exist_ok=True)

                html_file = f"{error_dir}/checkAssignments_error_{timestamp}.html"
                screenshot_file = f"{error_dir}/checkAssignments_error_{timestamp}.png"

                try:
                    print(f"A playwright error occurred: {e}")
                    if browser and browser.pages:
                        page = browser.pages[0]
                        with open(html_file, "w", encoding="utf-8") as f:
                            f.write(page.content())
                        page.screenshot(path=screenshot_file, full_page=True)
                        print(f"Saved debug HTML to: {html_file}")
                        print(f"Saved screenshot to: {screenshot_file}")
                        browser.close()
                
                except Exception as inner_e:
                    print(f"Failed to save debug info: {inner_e}")
            exit(1)

        clear_terminal()

        if args.whatsapp:
            display_whatsapp_formatted_deadlines(deadlines)
        else:
            display_deadlines(deadlines, args.kde, args.ntfy)
        
        if args.download_assignments:
            cleanup_old_files(download_dir, patterns, args.debug)

        if check_updates:
            check_for_updates()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        exit(1)