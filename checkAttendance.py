from playwright.sync_api import sync_playwright, BrowserContext, Page
from datetime import datetime
import argparse
import requests
import os
from dotenv import load_dotenv
from time import sleep

load_dotenv()
enrollment_number = os.getenv("ENROLLMENT_NUMBER", "")
password = os.getenv("PASSWORD", "")
data_dir = os.getenv("USER_DATA_DIR", "")
instituition = int(os.getenv("INSTITUTION", "6"))
check_updates = int(os.getenv("CHECK_UPDATES", "1"))

def format_number(n):
    """
    @brief Formats a number to 2 decimal places, removing trailing zeros and decimal points.
    @param n The number to format.
    @return Formatted string representation of the number.
    """
    return f"{n:.2f}".rstrip('0').rstrip('.')

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

def check_and_login_to_CMS(browser, page, debug_mode: bool):
    """
    @brief Authenticates user and navigates to the attendance page, handling login if needed.
    @param browser The BrowserContext object for managing cookies.
    @param page The Playwright page object to interact with.
    @param debug_mode Boolean flag to enable debug output.
    @return None
    """
    page.goto("https://cms.bahria.edu.pk/Sys/Student/ClassAttendance/StudentWiseAttendance.aspx")
    if "Login.aspx" in page.url:
        if debug_mode:
            print("Login required. Navigating to login page...")
        page.fill("#BodyPH_tbEnrollment", enrollment_number)
        page.fill("#BodyPH_tbPassword", password)
        page.select_option("#BodyPH_ddlInstituteID", "1")
        page.click(f"#pageContent > div.container-fluid > div.row > div > div:nth-child({instituition})")

        persist_cookies(browser, debug_mode)
        page.goto("https://cms.bahria.edu.pk/Sys/Student/ClassAttendance/StudentWiseAttendance.aspx")

    else:
        logged_in_enrollment_number = page.locator("#ProfileInfo_lblUsername").text_content().strip()
        if enrollment_number not in logged_in_enrollment_number:
            if debug_mode:
                print("Logged in with a different account. Logging out...")
            page.click("#AccountsNavbar > ul")
            page.click("#ProfileInfo_hlLogoff")
            check_and_login_to_CMS(page, browser, debug_mode)

def persist_cookies(browser, debug_mode: bool):
    """
    @brief Makes CMS cookies persistent for a year.
    @param browser The BrowserContext object containing the cookies.
    @param debug_mode Boolean flag to enable debug output.
    @return None
    """
    cookies = browser.cookies()
    for cookie in cookies:
        if cookie["name"] == "cms":
            cookie["expires"] = datetime.now().timestamp() + 31536000
            cookie["session"] = False
            browser.add_cookies([cookie])
            if debug_mode:
                print(f"Made {cookie['name']} cookie persistent.")

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

def scrape_attendance(page: Page, debug_mode: bool):
    """
    @brief Extracts and displays attendance statistics for all subjects.
    @param page The Playwright page object containing attendance data.
    @param debug_mode Boolean flag to enable debug output.
    @return None
    """
    rows = page.locator("#pageContent > div.container-fluid > div.table-responsive > table > tbody > tr").all()
    for row in rows:
        cells = row.locator("td").all()
        subject = cells[2].inner_text().strip()
        credits = cells[3].inner_text().strip()
        absences = cells[10].inner_text().strip()

        if debug_mode:
            print(f"Processing subject: {subject}, Credits: {credits}, Absences: {absences}")

        if credits == "0":
            credits = "1"
            if debug_mode:
                print(f"Credits for {subject} was 0, setting to 1 to avoid division by zero.")

        if(subject.split()[-1] == "Lab"):
            max_absences = int(credits) * 12
        else:
            max_absences = int(credits) * 4
        absences_remaining = max_absences - float(absences)

        if subject.split()[-1] == "Lab":
            if int(format_number(absences_remaining / (int(credits) * 3))) <= 2:
                print(f"\033[1;97m{subject}\033[0m: \033[1;91m{format_number(absences_remaining / (int(credits) * 3))}/{int(max_absences / (int(credits) * 3))}\033[0m")
            else:
                print(f"\033[1;97m{subject}\033[0m: {format_number(absences_remaining / (int(credits) * 3))}/{int(max_absences / (int(credits) * 3))}")
        
        else:
            if int(format_number(absences_remaining / int(credits) * 2)) <= 2:
                print(f"\033[1;97m{subject}\033[0m: \033[1;91m{format_number((absences_remaining / int(credits) * 2))}/{int(max_absences / int(credits) * 2)}\033[0m")
            else:
                print(f"\033[1;97m{subject}\033[0m: {format_number((absences_remaining / int(credits) * 2))}/{int(max_absences / int(credits) * 2)}")

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
        if enrollment_number == "" or password == "" or data_dir == "":
            print("Error: ENROLLMENT_NUMBER, PASSWORD, and USER_DATA_DIR must be set in the .env file.")
            exit(1)

        args = parse_args()
        browser = None

        try:
            with sync_playwright() as p:
                browser = start_playwright(args.debug)
                page = browser.pages[0]
                check_and_login_to_CMS(browser, page, args.debug)
                scrape_attendance(page, args.debug)
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

                html_file = f"{error_dir}/checkAttendance_error_{timestamp}.html"
                screenshot_file = f"{error_dir}/checkAttendance_error_{timestamp}.png"

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
        
        if check_updates:
            check_for_updates()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        exit(1)