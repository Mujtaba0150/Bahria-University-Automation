from playwright.sync_api import sync_playwright
from datetime import datetime
from dotenv import load_dotenv
import os
import argparse
from time import sleep

load_dotenv()
enrollment_number = os.getenv("ENROLLMENT_NUMBER", "")
password = os.getenv("PASSWORD", "")

def loginToCMS(page, browser, debug_mode: bool):
    """Handles login and cookie persistence."""
    page.goto("https://cms.bahria.edu.pk/Sys/Student/QualityAssurance/QualityAssuranceSurveys.aspx")
    
    if "Login.aspx" in page.url or "Default.aspx" in page.url:
        if debug_mode:
            print("Login required. Navigating to login page...")

        page.goto("https://cms.bahria.edu.pk/Logins/Student/Login.aspx")
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

# Format: BodyPH_surveyUserControl_repeaterQuestionGroups_repeaterQuestions_{section}_rbl_{question_number}_{option}_{question_number}
def fillSurvey(page, debug_mode: bool, option: int):
    # Detect which survey is loaded
    heading_element = page.wait_for_selector("#BodyPH_surveyUserControl_lbName")
    heading_text = heading_element.inner_text()

    # Question groups for both survey types
    teacher_groups = {
        0: 13,
        1: 5
    }

    course_groups = {
        0: 3,
        1: 3,
        2: 4,
        3: 4,
        4: 3,
        5: 3,
        6: 4,
        7: 3,
        8: 2
    }

    # Pick correct mapping
    groups = teacher_groups if "Teacher Evaluation Form" in heading_text else course_groups

    # Fill the survey
    for group_index, question_count in groups.items():
        for n in range(question_count):
            input_id = (
                f"BodyPH_surveyUserControl_repeaterQuestionGroups_"
                f"repeaterQuestions_{group_index}_rbl_{n}_{option}_{n}"
            )
            selector = f"#{input_id}"

            try:
                page.wait_for_selector(selector, timeout=2000)
                page.click(selector)
                if debug_mode:
                    print(f"Clicked: {input_id}")
            except Exception as e:
                if debug_mode:
                    print(f"Failed to click ({input_id}): {e}")

    # Submit
    submit_selector = "#BodyPH_surveyUserControl_btnSubmit"
    page.click(submit_selector)

    if debug_mode:
        print(f"Clicked: {submit_selector}")

def handleSurveys(page, debug_mode: bool, option: int):
    """Finds and fills all pending surveys."""
    page.goto("https://cms.bahria.edu.pk/Sys/Student/QualityAssurance/QualityAssuranceSurveys.aspx")
    page.wait_for_selector("#BodyPH_gvSurveyConducts")

    while True:
        rows = page.query_selector_all("#BodyPH_gvSurveyConducts > tbody > tr")

        if len(rows) == 0:
            break

        survey_links = extractSurveyLinks(rows, debug_mode)

        if not survey_links:
            break

        for href in survey_links:
            survey_url = "https://cms.bahria.edu.pk/Sys/Student/QualityAssurance/" + href
            page.goto(survey_url)
            fillSurvey(page, debug_mode, option)
            page.goto("https://cms.bahria.edu.pk/Sys/Student/QualityAssurance/QualityAssuranceSurveys.aspx")
            page.wait_for_selector("#BodyPH_gvSurveyConducts")

def extractSurveyLinks(rows, debug_mode: bool):
    """Extracts survey URLs from table rows."""
    survey_links = []
    for row in rows:
        link = row.query_selector("td:last-child a")
        if link:
            href = link.get_attribute("href")
            if href and "SurveyStudentCourseWise" in href:
                survey_links.append(href)
    if debug_mode:
        print(f"Extracted {len(survey_links)} survey links.")
    return survey_links

def startPlaywright(debug_mode: bool):
    """Launches persistent browser and runs survey automation."""
    browser = p.chromium.launch_persistent_context(
        user_data_dir="/home/mujtaba0150/.config/ms-playwright",
        headless= not debug_mode,
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

def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    return parser.parse_args()

if __name__ == "__main__":
    args = parseArgs()

    # ask which option to use
    chosen_option = int(input(
        "Select your answer option (0=Strongly Agree, 1=Agree, 2=Uncertain, 3=Disagree, 4=Strongly Disagree): "
    ))

    with sync_playwright() as p:
        browser = startPlaywright(args.debug)
        page = browser.pages[0]
        loginToCMS(page, browser, args.debug)

        # pass the chosen option to survey handling
        handleSurveys(page, args.debug, chosen_option)

        browser.close()
