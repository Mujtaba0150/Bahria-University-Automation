from playwright.sync_api import sync_playwright
from datetime import datetime
from dotenv import load_dotenv
from time import sleep
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

load_dotenv()
download_dir = os.getenv("DOWNLOAD_DIR", "")
enrollment_number = os.getenv("ENROLLMENT_NUMBER", "")
password = os.getenv("PASSWORD", "")
data_dir = os.getenv("USER_DATA_DIR", "")

def clean_text(text: str) -> str:
    return " ".join(text.split())

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-k", "--kde", action="store", help="Send notifications via KDE Connect using Device ID")
    parser.add_argument("-n", "--ntfy", action="store", help="Send notifications via Ntfy using Server")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode")
    return parser.parse_args()


def check_and_login(page, browser, debug_mode: bool):
    page.goto("https://lms.bahria.edu.pk/Student/Assignments.php")
    if  ("https://lms.bahria.edu.pk/" in page.url):
        logged_in = page.locator("body > div > header > nav > div > ul > li.dropdown.user.user-menu > ul > li.user-header > p").text_content().strip()
        if enrollment_number not in logged_in:
            page.click("body > div > header > nav > div > ul > li.dropdown.user.user-menu")
            page.click("body > div > header > nav > div > ul > li.dropdown.user.user-menu.open > ul > li.user-footer > div.pull-right")
            if "Login.aspx" not in page.url:
                page.click("#AccountsNavbar > ul")
                page.click("#ProfileInfo_hlLogoff")
            if debug_mode:
                print("User logged out")
    
    if "cms.bahria.edu.pk" in page.url:
        page.goto("https://cms.bahria.edu.pk/Logins/Student/Login.aspx")
        if "Login.aspx" in page.url:
            page.fill("#BodyPH_tbEnrollment", enrollment_number)
            page.fill("#BodyPH_tbPassword", password)
            page.select_option("#BodyPH_ddlInstituteID", "1")
            page.click("#pageContent > div.container-fluid > div.row > div > div:nth-child(6)")
    
        lms_button = page.wait_for_selector("#sideMenuList > a:nth-child(16)")
        page.evaluate("el => el.removeAttribute('target')", lms_button)
        lms_button.click()

        cookies = browser.cookies()
        for cookie in cookies:
            if cookie["name"] in ["cms", "PHPSESSID"]:
                cookie["expires"] = (datetime.now().timestamp() + 31536000)
                cookie["session"] = False
                browser.add_cookies([cookie])
                if debug_mode:
                    print(f"Made {cookie['name']} cookie persistent.")

def download_assignment_file(page, subject_name: str, assignment_name: str, deadline_date: str, assignment_link: str) -> str:
    """
    Handles the downloading of an assignment file, creating directories if necessary,
    and returning the file pattern used to check for duplicates.
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
    """Delete all files and folders in download_dir that are not matched by any pattern."""
    allFiles = glob.glob(f"{download_dir}/**/*", recursive=True)
    keepFiles = set()
    for pattern in patterns:
        keepFiles.update(glob.glob(pattern))

    for path in allFiles:
        if os.path.isdir(path):
            continue
        if path not in keepFiles:
            try:
                os.remove(path)
                if debug_mode:
                    print(f"Deleted file: {path}")
            except Exception as e:
                print(f"Error deleting {path}: {e}")

    # Remove empty directories
    for root, dirs, _ in os.walk(download_dir, topdown=False):
        for d in dirs:
            fullPath = os.path.join(root, d)
            if not os.listdir(fullPath):
                try:
                    os.rmdir(fullPath)
                    if debug_mode:
                        print(f"Deleted empty directory: {fullPath}")
                except Exception as e:
                    print(f"Error deleting directory {fullPath}: {e}")

def fetch_assignments(debug_mode: bool) -> tuple[list, list]:
    deadlines = []
    patterns = []

    with sync_playwright() as p:
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
        page = browser.pages[0]
        check_and_login(page, browser, debug_mode)
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
                    assignment_name = cells[1].text_content().strip() # pyright: ignore[reportOptionalMemberAccess]
                    assignment_link = f"https://lms.bahria.edu.pk/Student/{cells[2].locator('a').get_attribute('href')}"
                    deadline_date = cells[7].locator("small").first.text_content().split('-')[0].strip() # pyright: ignore[reportOptionalMemberAccess]

                    pattern = download_assignment_file(page, subject_name, assignment_name, deadline_date, assignment_link) # pyright: ignore[reportArgumentType]

                    if deadline_date:
                        deadlines.append((subject_name, deadline_date))
                    patterns.append(pattern)

        browser.close()

    return deadlines, patterns


def display_deadlines(deadlines: list, kdeDevice: str, ntfyServer: str):
    today = datetime.today().date()
    parsedDeadlines = []
    for subject, date_str in deadlines:
        deadline_date = datetime.strptime(date_str, "%d %B %Y").date()
        days_left = (deadline_date - today).days
        parsedDeadlines.append((subject, deadline_date, days_left))

    parsedDeadlines.sort(key=lambda x: x[1])

    dueToday, dueNext4, dueAfter4, messages = [], [], [], []

    for subject, deadline_date, days_left in parsedDeadlines:
        display_date = deadline_date.strftime("%#d %B") if os.name == "nt" else deadline_date.strftime("%-d %B")
        plainMsg = f"{subject} - {display_date} ({days_left} Days Left)"
        if days_left == 0:
            colored = f"{Colors.RED_BRIGHT}{subject} - {display_date} (Due Today){Colors.RESET}"
            dueToday.append(colored)
            if kdeDevice or ntfyServer:
                messages.append(plainMsg)
        elif 1 <= days_left <= 4:
            color = [Colors.YELLOW_BRIGHT, Colors.YELLOW_MEDIUM, Colors.YELLOW_DARK][min(days_left - 1, 2)]
            colored = f"{color}{subject} - {display_date} ({days_left} Days Left){Colors.RESET}"
            dueNext4.append(colored)
        elif 5 <= days_left <= 7:
            color = Colors.GREEN_BRIGHT
            colored = f"{color}{subject} - {display_date} ({days_left} Days Left){Colors.RESET}"
            dueAfter4.append(colored)
        elif 8 <= days_left <= 14:
            color = Colors.GREEN_MEDIUM
            colored = f"{color}{subject} - {display_date} ({days_left} Days Left){Colors.RESET}"
            dueAfter4.append(colored)
        else:
            color = Colors.GREEN_DARK
            colored = f"{color}{subject} - {display_date} ({days_left} Days Left){Colors.RESET}"
            dueAfter4.append(colored)

    if dueToday:
        print("=== Due Today ===")
        for line in dueToday:
            print(line)
        print()

    if dueNext4:
        print("=== Due Within the Next 4 Days ===")
        for line in dueNext4:
            print(line)
        print()

    if dueAfter4:
        print("=== Due After 4 Days ===")
        for line in dueAfter4:
            print(line)
        print()

    if kdeDevice and messages:
        for msg in messages:
            subprocess.run(["kdeconnect-cli", "--device", kdeDevice, "--ping-msg", msg])
    if ntfyServer and messages:
        for msg in messages:
            url = f"https://ntfy.sh/{ntfyServer}"
            headers = {
            "Title": "Assignments Due Today",
            "Priority": "5"
            }
            requests.post(url, data=msg, headers=headers)

if __name__ == "__main__":
    if download_dir == "" or enrollment_number == "" or password == "" or data_dir == "":
        print("Error: One or more required environment variables are not set.")
        exit(1)
    args = parse_args()
    deadlines, patterns = fetch_assignments(args.debug)
    
    display_deadlines(deadlines, args.kde, args.ntfy)
    cleanup_old_files(download_dir, patterns, args.debug)
