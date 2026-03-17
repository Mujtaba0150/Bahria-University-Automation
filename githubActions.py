from playwright.sync_api import sync_playwright, Page
from datetime import datetime
from dotenv import load_dotenv
from time import sleep
import requests
import os

load_dotenv()
enrollment_number = os.getenv("ENROLLMENT_NUMBER", "")
password = os.getenv("PASSWORD", "")
notification_level = int(os.getenv("NOTIFICATION_LEVEL", "0"))
notify_extended = int(os.getenv("NOTIFY_EXTENDED", "1"))
instituition = int(os.getenv("INSTITUTION", "6"))
ntfy_server = os.getenv("NTFY_SERVER", "")
download_assignments = int(os.getenv("DOWNLOAD_ASSIGNMENTS", "0"))

def clean_text(text: str) -> str:
    """
    @brief Removes extra whitespace from text by collapsing multiple spaces into single spaces.
    @param text The input string to clean.
    @return String with normalized whitespace.
    """
    return " ".join(text.split())

def start_playwright():
    """
    @brief Launches a headless Chromium browser with optimized settings.
    @return Browser object with no persistent context.
    """
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

def send_notification(title, message: str, priority: int, file_path: str = ""):
    """
    @brief Sends a notification via ntfy.sh service with optional file attachment.
    @param title The title of the notification.
    @param message The message body of the notification.
    @param priority The priority level of the notification (1-5).
    @param file_path Optional file path to attach to the notification.
    @return None
    """
    if ntfy_server and file_path != "":
        requests.put(
            f"https://ntfy.sh/{ntfy_server}",
            data=open(file_path, 'rb'),
            headers={"Title": title, "Priority": str(priority), "File": os.path.basename(file_path)},
            params={
                "message": message,
            }
        )
    elif ntfy_server:
        requests.post(
            f"https://ntfy.sh/{ntfy_server}",
            data=message.encode('utf-8'),
            headers={"Title": title, "Priority": str(priority)},
        )
    else:
        print("ntfy_server is not set. Cannot send notification.")

def check_and_login(page):
    """
    @brief Authenticates user and ensures proper LMS access for assignment retrieval.
    @param page The Playwright page object to interact with.
    @return None
    """
    page.goto("https://cms.bahria.edu.pk/Logins/Student/Login.aspx")
    page.fill("#BodyPH_tbEnrollment", enrollment_number)
    page.fill("#BodyPH_tbPassword", password)
    page.select_option("#BodyPH_ddlInstituteID", "1")
    page.click(f"#pageContent > div.container-fluid > div.row > div > div:nth-child({instituition})")
    print(f"Logged in as {enrollment_number}")
    lms_button = page.wait_for_selector("#sideMenuList > a:nth-child(16)")
    page.evaluate("el => el.removeAttribute('target')", lms_button)
    lms_button.click()
    
    if ("QualityAssuranceSurveys.aspx" in page.url):
        print("Please complete the Quality Assurance Survey to proceed.")   
        send_notification("Error" ,"Please complete the Quality Assurance Survey to proceed.", 2)
        exit(1)

def download_assignment_file(page, subject_name: str, assignment_name: str, deadline_date: str, assignment_link: str) -> str:
    """
    @brief Downloads an assignment file and saves it in a subject-specific directory.
    @param page The Playwright page object to interact with.
    @param subject_name The name of the subject for the assignment.
    @param assignment_name The name of the assignment.
    @param deadline_date The deadline date formatted as string.
    @param assignment_link The URL link to the assignment file.
    @return The final path of the downloaded assignment file.
    """
    if not os.path.exists(f"{os.environ.get('HOME')}/{subject_name}"):
        os.makedirs(f"{os.environ.get('HOME')}/{subject_name}")

    subject_dir = f"{os.environ.get('HOME')}/{subject_name}"
    file_base = f"{assignment_name} - {deadline_date}"
    
    with page.expect_download() as download_info:
        page.evaluate(f"window.location.href = '{assignment_link}'")
    
    download = download_info.value
    file_name = download.suggested_filename
    _, file_ext = os.path.splitext(file_name)
    final_path = os.path.join(subject_dir, f"{file_base}{file_ext}")
    download.save_as(final_path)

    return final_path

def fetch_assignments(page: Page) -> list:
    """
    @brief Fetches all assignments from the LMS with their deadlines and file paths.
    @param page The Playwright page object to interact with.
    @return List of tuples containing assignment number, subject, deadline, submitted status, extended flag, and file path.
    """
    deadlines = []
    final_path = None

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
                deadline_col = cells[7].locator("small")
                deadline_title = deadline_col.first.get_attribute("title") or ""
                extended = "Extended" in deadline_title
                submitted = "Delete" in action_col # pyright: ignore[reportOperatorIssue]
                assignment_number = cells[0].text_content().strip() # pyright: ignore[reportOptionalMemberAccess]
                assignment_name = cells[1].text_content().strip() # pyright: ignore[reportOptionalMemberAccess]
                deadline_date = deadline_col.first.text_content().split('-')[0].strip() # pyright: ignore[reportOptionalMemberAccess]

                if download_assignments:
                    assignment_link = f"https://lms.bahria.edu.pk/Student/{cells[2].first.locator('a').first.get_attribute('href')}"
                    final_path = download_assignment_file(page, subject_name, assignment_name, deadline_date, assignment_link)
                
                if deadline_date:
                    deadlines.append((assignment_number, subject_name, deadline_date, submitted, extended, final_path if download_assignments else None))
    return deadlines

def alert_deadline(deadlines: list, ntfy_server: str):
    """
    @brief Processes deadlines and sends notifications based on time remaining and notification level.
    @param deadlines List of tuples containing assignment deadline information.
    @param ntfy_server The ntfy service name for sending notifications.
    @return None
    """
    today = datetime.today().date()
    parsed_deadlines = []

    for assignment_number, subject, date_str, submitted, extended, final_path in deadlines:
        deadline_date = datetime.strptime(date_str, "%d %B %Y").date()
        days_left = (deadline_date - today).days
        parsed_deadlines.append((assignment_number, subject, deadline_date, days_left, submitted, extended, final_path))

    parsed_deadlines.sort(key=lambda x: x[3])

    level_to_max_days = {0: 0, 1: 4, 2: 7, 3: 14, 4: float("inf")}
    max_days_for_notification = level_to_max_days.get(notification_level, 0)

    notifications = []

    for assignment_number, subject, deadline_date, days_left, submitted, extended, final_path in parsed_deadlines:
        display_date = deadline_date.strftime("%-d %B")
        notification_message = f"{assignment_number}. {subject} - {display_date} {'Submitted' if submitted else ''}"

        if days_left <= max_days_for_notification and (not submitted or (notify_extended and extended)):
            priority = 5 if days_left == 0 else 4 if days_left <= 4 else 3
            notifications.append((notification_message, days_left, priority, submitted, extended, final_path))

    for notification, days_left, priority, submitted, extended, final_path in notifications:
            if ntfy_server and (not submitted or (notify_extended and extended)):
                if days_left == 0:
                    send_notification("Assignment Due Today", notification, priority, final_path if final_path else "")
                elif days_left <= 4:
                    send_notification("Assignment Due in Next 4 Days", notification, priority, final_path if final_path else "")
                elif days_left <= 7:
                    send_notification("Assignment Due in Next 7 Days", notification, priority, final_path if final_path else "")
                elif days_left <= 14:
                    send_notification("Assignment Due in Next 14 Days", notification, priority, final_path if final_path else "")
                else:
                    send_notification("Upcoming Assignments", notification, priority, final_path if final_path else "")

def format_number(n):
    """
    @brief Formats a number to 2 decimal places, removing trailing zeros and decimal points.
    @param n The number to format.
    @return Formatted string representation of the number.
    """
    return f"{n:.2f}".rstrip('0').rstrip('.')


def alert_attendance(subject):
    """
    @brief Sends a notification alert when attendance drops below allowed absence limit.
    @param subject The name of the subject with critical attendance.
    @return None
    """
    try:
        response = requests.post(
            f"https://ntfy.sh/{ntfy_server}",
            data=f"Your attendance for {subject} has exceeded the allowed absence limit.",
            headers={"Title": f"Attendance Alert: {subject}", "Priority": "5"},
            timeout=5
        )
        response.raise_for_status()
        print(f"Notification sent for {subject}")
    except requests.RequestException as e:
        print(f"Failed to send notification for {subject}: {e}")

def scrape_attendance(page: Page, debug_mode: bool):
    """
    @brief Extracts and displays attendance statistics for all subjects, alerting if limits are exceeded.
    @param page The Playwright page object containing attendance data.
    @param debug_mode Boolean flag to enable debug output.
    @return None
    """
    page.goto("https://cms.bahria.edu.pk/Sys/Student/ClassAttendance/StudentWiseAttendance.aspx")
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
            if int(format_number(absences_remaining / (int(credits) * 3))) < 0:
                alert_attendance(subject)
        else:
            if int(format_number(absences_remaining / int(credits) * 2)) < 0:
                alert_attendance(subject)


if __name__ == "__main__":
    try:
        if enrollment_number == "" or password == "" or notification_level < 0 or notification_level > 4 or ntfy_server == "":
            print("Error: One or more required environment variables are not set or are incorrectly set.")
            send_notification("Error", "Error: One or more required environment variables are not set or are incorrectly set.", 1)
            if enrollment_number == "":
                print("ENROLLMENT_NUMBER is not set.")
            if password == "":
                print("PASSWORD is not set.")
            if notification_level < 0 or notification_level > 4:
                print("NOTIFICATION_LEVEL must be an integer between 0 and 4.")
            if ntfy_server == "":
                print("NTFY_SERVER is not set.")
            exit(1)

        browser = None
        with sync_playwright() as p:
            browser = start_playwright()
            
            context = browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = context.new_page()
            
            # sleep(2000000)
            check_and_login(page)
            deadlines = fetch_assignments(page)
            alert_deadline(deadlines, ntfy_server)
            scrape_attendance(page, debug_mode=False)
            
            browser.close()
    except Exception as e:
        print(f"Error during automation: {str(e)}")
        send_notification("Error", f"Error during automation: {str(e)}", 1)
    finally:
        exit(0)