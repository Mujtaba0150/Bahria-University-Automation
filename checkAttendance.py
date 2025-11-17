from playwright.sync_api import sync_playwright, BrowserContext, Page
from datetime import datetime
import argparse
import os
from dotenv import load_dotenv
from time import sleep

load_dotenv()
enrollment_number = os.getenv("ENROLLMENT_NUMBER", "")
password = os.getenv("PASSWORD", "")
data_dir = os.getenv("USER_DATA_DIR", "")

def loginToCMS(page, browser, debug_mode: bool):
    """Handles login and cookie persistence."""
    page.goto("https://cms.bahria.edu.pk/Logins/Student/Login.aspx")
    sleep(15)

    if "Login.aspx" in page.url:
        if debug_mode:
            print("Login required. Navigating to login page...")
        page.fill("#BodyPH_tbEnrollment", enrollment_number)
        page.fill("#BodyPH_tbPassword", password)
        page.select_option("#BodyPH_ddlInstituteID", "1")
        page.click("#pageContent > div.container-fluid > div.row > div > div:nth-child(6)")

        lms_button = page.wait_for_selector("#sideMenuList > a:nth-child(16)")
        page.evaluate("el => el.removeAttribute('target')", lms_button)
        lms_button.click()

        persistCookies(browser, debug_mode)

def persistCookies(browser, debug_mode: bool):
    """Makes CMS cookies persistent for a year."""
    cookies = browser.cookies()
    for cookie in cookies:
        if cookie["name"] in ["cms", "PHPSESSID"]:
            cookie["expires"] = datetime.now().timestamp() + 31536000
            cookie["session"] = False
            browser.add_cookies([cookie])
            if debug_mode:
                print(f"Made {cookie['name']} cookie persistent.")

def startPlaywright(debug_mode: bool) -> BrowserContext:
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

def scrapeAttendance(page: Page, debug_mode: bool):
    """Multiply by 4 so for 1 credit hour course u can be absent for 4 hours, for 2 u can be absent for 8 etc (it works slightly differently for lab because it has 3 contact hours so u can be absent for 12 hours)."""

    page.goto("https://cms.bahria.edu.pk/Sys/Student/ClassAttendance/StudentWiseAttendance.aspx")
    rows = page.locator("#pageContent > div.container-fluid > div.table-responsive > table > tbody > tr").all()
    for row in rows:
        cells = row.locator("td").all()
        subject = cells[2].inner_text().strip()
        credits = cells[3].inner_text().strip()
        absences = cells[10].inner_text().strip()
        if(subject.split()[-1] == "Lab"):
            max_absences = float(credits) * 12
        else:
            max_absences = float(credits) * 4
        absences_remaining = max_absences - float(absences)

        if subject.split()[-1] == "Lab":
            print(f"\033[1;97m{subject}\033[0m: {absences_remaining / (float(credits) * 3)}/{max_absences / (float(credits) * 3)}")
        else:
            print(f"\033[1;97m{subject}\033[0m: {absences_remaining / float(credits) * 2}/{max_absences / float(credits) * 2}")


def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    return parser.parse_args()

if __name__ == "__main__":
    if enrollment_number == "" or password == "" or data_dir == "":
        print("Error: ENROLLMENT_NUMBER, PASSWORD, and USER_DATA_DIR must be set in the .env file.")
        exit(1)
    with sync_playwright() as p:
        args = parseArgs()
        browser = startPlaywright(args.debug)
        page = browser.pages[0]
        loginToCMS(page, browser, args.debug)
        scrapeAttendance(page, args.debug)
        browser.close()