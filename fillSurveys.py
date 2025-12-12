from playwright.sync_api import sync_playwright
from datetime import datetime
from dotenv import load_dotenv
import os
import platform
import argparse
from time import sleep

load_dotenv()
enrollment_number = os.getenv("ENROLLMENT_NUMBER", "")
password = os.getenv("PASSWORD", "")
data_dir = os.getenv("USER_DATA_DIR", "")
disabled = os.getenv("DISABLED", 0)
gender = os.getenv("GENDER", 0)
age = os.getenv("AGE", 0)
on_campus = os.getenv("ON_CAMPUS", 1)


def clear_terminal():
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")

def start_playwright(debug_mode: bool):
    """Launches persistent browser and runs survey automation."""
    browser = p.chromium.launch_persistent_context(
        user_data_dir=data_dir,
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

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug mode")
    return parser.parse_args()

def check_and_login_to_CMS(page, debug_mode: bool):
    """Handles login and cookie persistence."""
    page.goto("https://cms.bahria.edu.pk/Sys/Student/QualityAssurance/QualityAssuranceSurveys.aspx")
    
    if "Login.aspx" in page.url in page.url:
        if debug_mode:
            print("Login required. Navigating to login page...")

        page.goto("https://cms.bahria.edu.pk/Logins/Student/Login.aspx")
        page.fill("#BodyPH_tbEnrollment", enrollment_number)
        page.fill("#BodyPH_tbPassword", password)
        page.select_option("#BodyPH_ddlInstituteID", "1")
        page.click("#pageContent > div.container-fluid > div.row > div > div:nth-child(6)")

        persist_cookies(browser, debug_mode)
        page.goto("https://cms.bahria.edu.pk/Sys/Student/QualityAssurance/QualityAssuranceSurveys.aspx")

    else:
        logged_in_enrollment_number = page.locator("#ProfileInfo_lblUsername").text_content().strip()
        if enrollment_number not in logged_in_enrollment_number:
            if debug_mode:
                print("Logged in with a different account. Logging out...")
            page.click("#AccountsNavbar > ul")
            page.click("#ProfileInfo_hlLogoff")
            check_and_login_to_CMS(page, debug_mode)

def persist_cookies(browser, debug_mode: bool):
    """Makes CMS cookies persistent for a year."""
    cookies = browser.cookies()
    for cookie in cookies:
        if cookie["name"] == "cms":
            cookie["expires"] = datetime.now().timestamp() + 31536000
            cookie["session"] = False
            browser.add_cookies([cookie])
            if debug_mode:
                print(f"Made {cookie['name']} cookie persistent.")

def handle_surveys(page, option: int, debug_mode: bool):
    """Finds and fills all pending surveys."""
    page.goto("https://cms.bahria.edu.pk/Sys/Student/QualityAssurance/QualityAssuranceSurveys.aspx")
    page.wait_for_selector("#BodyPH_gvSurveyConducts")

    rows = page.query_selector_all("#BodyPH_gvSurveyConducts > tbody > tr")
    survey_data = extract_survey_data(rows, debug_mode)
    clear_terminal()
    for survey in survey_data:
        print(f"{survey['sr_no']}: {survey['course']} - {survey['teacher']}({survey['survey_name']})")

    custom_input = input("\nEnter the survey numbers to fill manually (comma-separated), or press Enter to fill all: ")
    custom_input = [x.strip() for x in custom_input.split(",")]
    
    for survey in survey_data:
        survey_url = "https://cms.bahria.edu.pk/Sys/Student/QualityAssurance/" + survey["url"]
        page.goto(survey_url)
        
        currently_filling = f"Filling survey: {survey['course']} - {survey['teacher']}({survey['survey_name']})"
        
        if survey["sr_no"] in custom_input:
            fill_custom_survey(page, currently_filling, debug_mode)
        else:
            fill_survey(page, debug_mode, option)

def extract_survey_data(rows, debug_mode: bool):
    """Extracts survey URLs from table rows."""
    survey_data = []
    for row in rows:
        sr_no = row.query_selector("td:nth-child(1)")
        survey_name_cell = row.query_selector("td:nth-child(3)")
        course_cell = row.query_selector("td:nth-child(4)")
        teacher_cell = row.query_selector("td:nth-child(5)")
        link = row.query_selector("td:last-child a")

        course_title = course_cell.evaluate("""
        (element) => {
            return Array.from(element.childNodes)
                .filter(node => node.nodeType === Node.TEXT_NODE)
                .map(node => node.textContent.trim())
                .filter(text => text.length > 0)[0] || "";
        }
        """)

        if link:
            href = link.get_attribute("href")
            if href and "SurveyStudentCourseWise" in href:
                teacher_name = teacher_cell.inner_text().strip() if teacher_cell else None
                sr_no_text = sr_no.inner_text().strip() if sr_no else None
                survey_name = survey_name_cell.inner_text().strip() if survey_name_cell else "None"
                
                survey_data.append({
                    "sr_no": sr_no_text,
                    "survey_name": survey_name[:-16].strip(),
                    "url": href,
                    "teacher": teacher_name,
                    "course": course_title
                })
    if debug_mode:
        print(f"Extracted {len(survey_data)} surveys.")
    return survey_data

# Format: BodyPH_surveyUserControl_repeaterQuestionGroups_repeaterQuestions_{section}_rbl_{question_number}_{option}_{question_number}
def fill_survey(page, debug_mode: bool, option: int):
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
        for question_number in range(question_count):
            if question_number == 0 and group_index == 1 and groups == course_groups:
                input_id = (
                    f"BodyPH_surveyUserControl_repeaterQuestionGroups_"
                    f"repeaterQuestions_{group_index}_rbl_{question_number}_{4}_{question_number}"
                )
            else:
                input_id = (
                    f"BodyPH_surveyUserControl_repeaterQuestionGroups_"
                    f"repeaterQuestions_{group_index}_rbl_{question_number}_{option}_{question_number}"
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

    if groups == course_groups: 
        fill_demographic_info(page)
    
    # Submit
    submit_selector = "#BodyPH_surveyUserControl_btnSubmit"
    page.click(submit_selector)

    if debug_mode:
        print(f"Clicked: {submit_selector}")

def fill_custom_survey(page, currently_filling, debug_mode: bool):
    """Handles custom surveys not following standard format."""
    if debug_mode:
        print("Custom survey detected. Manual intervention required.")
    
    clear_terminal()
    print(currently_filling + "\n")
    choice = int(input("Do you want to fill the same value for all questions? (0=No, 1=Yes): "))

    if choice == 1:
        selected_option = int(input(
            "Select your default answer option (0=Strongly Agree, 1=Agree, 2=Uncertain, 3=Disagree, 4=Strongly Disagree): "
        ))
        fill_survey(page, debug_mode, selected_option)
    
    else:
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
        for group_index, question_count in groups.items():
            for question_number in range(question_count):
                question_selector = f"#BodyPH_surveyUserControl_repeaterQuestionGroups_repeaterQuestions_{group_index}_divOptions_{question_number} > label"
                question = page.query_selector(question_selector)
                if question:
                    clear_terminal()
                    print(currently_filling + "\n")
                    print(f"Question: {question.inner_text().strip()}")
                    if question_number == 0 and group_index == 1 and groups == course_groups:
                        selected_option = int(input(
                            "Select your answer option (0=<21%, 1=21-40%, 2=41-60%, 3=61-80%, 4=>80%): "
                        ))
                    else:
                        selected_option = int(input(
                            "Select your answer option (0=Strongly Agree, 1=Agree, 2=Uncertain, 3=Disagree, 4=Strongly Disagree): "
                        ))
                    input_id = (
                        f"BodyPH_surveyUserControl_repeaterQuestionGroups_"
                        f"repeaterQuestions_{group_index}_rbl_{question_number}_{selected_option}_{question_number}"
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
        if groups == course_groups: 
            fill_demographic_info(page)

        # Submit
        submit_selector = "#BodyPH_surveyUserControl_btnSubmit"
        page.click(submit_selector)

def fill_demographic_info(page):
    # Fulltime/Parttime
    page.wait_for_selector("#BodyPH_surveyUserControl_repeaterQuestionGroups_repeaterQuestions_11_rbl_0_1_0", timeout=2000)
    page.click("#BodyPH_surveyUserControl_repeaterQuestionGroups_repeaterQuestions_11_rbl_0_1_0")
    
    # Disabled/Non-Disabled
    selector = f"#BodyPH_surveyUserControl_repeaterQuestionGroups_repeaterQuestions_11_rbl_1_{not disabled}_1"
    page.wait_for_selector(selector, timeout=2000)
    page.click(selector)
    
    # Male/Female
    page.wait_for_selector(f"#BodyPH_surveyUserControl_repeaterQuestionGroups_repeaterQuestions_11_rbl_3_{gender}_3", timeout=2000)
    page.click(f"#BodyPH_surveyUserControl_repeaterQuestionGroups_repeaterQuestions_11_rbl_3_{gender}_3")
    
    # Age:>22/22-29/>29
    page.wait_for_selector(f"#BodyPH_surveyUserControl_repeaterQuestionGroups_repeaterQuestions_11_rbl_4_{age}_4", timeout=2000)
    page.click(f"#BodyPH_surveyUserControl_repeaterQuestionGroups_repeaterQuestions_11_rbl_4_{age}_4")
    
    # On Campus/Off Campus
    page.wait_for_selector(f"#BodyPH_surveyUserControl_repeaterQuestionGroups_repeaterQuestions_11_rbl_5_{on_campus}_5", timeout=2000)
    page.click(f"#BodyPH_surveyUserControl_repeaterQuestionGroups_repeaterQuestions_11_rbl_5_{on_campus}_5")

if __name__ == "__main__":

    if enrollment_number == "" or password == "" or data_dir == "":
        print("Error: One or more required environment variables are not set.")
        exit(1)

    args = parse_args()

    chosen_option = int(input(
        "Select your default answer option (0=Strongly Agree, 1=Agree, 2=Uncertain, 3=Disagree, 4=Strongly Disagree): "
    ))

    with sync_playwright() as p:
        browser = start_playwright(args.debug)
        page = browser.pages[0]
        check_and_login_to_CMS(page, args.debug)

        handle_surveys(page, chosen_option, args.debug)

        browser.close()
