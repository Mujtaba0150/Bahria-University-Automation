from playwright.sync_api import sync_playwright, Page
from datetime import datetime
from dotenv import load_dotenv
from time import sleep
import requests
import os

load_dotenv()
enrollment_number = os.getenv("ENROLLMENT_NUMBER", "")
password = os.getenv("PASSWORD", "")

notification_level = int(os.getenv("NOTIFICATION_LEVEL", "0")) if os.getenv("NOTIFICATION_LEVEL", "0").isdigit() else 0
notify_submitted = os.getenv("NOTIFY_SUBMITTED", "1") == "1"
instituition = int(os.getenv("INSTITUTION", "6")) if os.getenv("INSTITUTION", "6").isdigit() else 6

ntfy_server = os.getenv("NTFY_SERVER", "")

def clean_text(text: str) -> str:
    return " ".join(text.split())

def start_playwright():
    """Launches browser and runs survey automation."""
    browser = p.chromium.launch(
        headless=True,
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

def send_notification(message: str, priority: int, ntfy_server: str = ntfy_server):
    if ntfy_server:
        requests.post(
            f"https://ntfy.sh/{ntfy_server}",
            data=message,
            headers={"Title": "Assignments Due Today", "Priority": str(priority)}
        )

def check_and_login(page):
    '''Handles login and cookie persistence.'''
    page.goto("https://lms.bahria.edu.pk/Student/Assignments.php")
    if  ("https://lms.bahria.edu.pk/" in page.url):
        logged_in_enrollment_number = page.locator("body > div > header > nav > div > ul > li.dropdown.user.user-menu > ul > li.user-header > p").text_content().strip()
        if enrollment_number not in logged_in_enrollment_number:
            page.click("body > div > header > nav > div > ul > li.dropdown.user.user-menu")
            page.click("body > div > header > nav > div > ul > li.dropdown.user.user-menu.open > ul > li.user-footer > div.pull-right")
            if "Dashboard.aspx" in page.url:
                page.click("#AccountsNavbar > ul")
                page.click("#ProfileInfo_hlLogoff")
            check_and_login(page)
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
            send_notification("Please complete the Quality Assurance Survey to proceed.", 2)

def fetch_assignments(page: Page) -> tuple[list, list]:
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
                
                if deadline_date:
                    deadlines.append((assignment_number, subject_name, deadline_date, submitted))

    return deadlines, patterns

def alert_deadline(deadlines: list, ntfy_server: str):
    today = datetime.today().date()
    parsed_deadlines = []

    for assignment_number, subject, date_str, submitted in deadlines:
        deadline_date = datetime.strptime(date_str, "%d %B %Y").date()
        days_left = (deadline_date - today).days
        parsed_deadlines.append((assignment_number, subject, deadline_date, days_left, submitted))

    parsed_deadlines.sort(key=lambda x: x[3])

    level_to_max_days = {0: 0, 1: 4, 2: 7, 3: 14, 4: float("inf")}
    max_days_for_notification = level_to_max_days.get(notification_level, 0)

    notifications = []

    for assignment_number, subject, deadline_date, days_left, submitted in parsed_deadlines:
        display_date = deadline_date.strftime("%#d %B") if os.name == "nt" else deadline_date.strftime("%-d %B")
        notification_message = f"{assignment_number}. {subject} - {display_date} {'Submitted' if submitted else ''}"

        if days_left <= max_days_for_notification and (not submitted or notify_submitted):
            priority = 5 if days_left == 0 else 4 if days_left <= 4 else 3
            notifications.append((notification_message, priority, submitted))

    for notification, priority, submitted in notifications:
        if ntfy_server:
            requests.post(
                f"https://ntfy.sh/{ntfy_server}",
                data=notification,
                headers={"Title": "Assignments Due Today", "Priority": str(priority)}
            )

if __name__ == "__main__":
    try:
        if enrollment_number == "" or password == "" or notification_level < 0 or notification_level > 4 or ntfy_server == "":
            print("Error: One or more required environment variables are not set or are incorrectly set.")
            send_notification("Error: One or more required environment variables are not set or are incorrectly set.", 1)
            exit(1)

        browser = None
        with sync_playwright() as p:
            browser = start_playwright()
            
            context = browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = context.new_page()
            
            # sleep(2000000)
            check_and_login(page)
            deadlines, patterns = fetch_assignments(page)
            alert_deadline(deadlines, ntfy_server)
            browser.close()
    except Exception as e:
        print(f"Error during automation: {str(e)}")
        send_notification(f"Error during automation: {str(e)}", 1)
    finally:
        if browser: # type: ignore
            browser.close()