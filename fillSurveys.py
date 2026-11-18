from playwright.sync_api import sync_playwright, Page
from time import sleep
import argparse
import sys

from functions import (
    ENROLLMENT_NUMBER, PASSWORD, USER_DATA_DIR, CHECK_UPDATES, CMS_SURVEYS_URL,
    DISABLED, GENDER, AGE, ON_CAMPUS,
    clear_terminal, check_for_updates,
    start_browser, get_page, close_browser, handle_script_error, ensure_cms_login,
)

# Number of questions in each question group, for both survey types
TEACHER_GROUPS = {
    0: 13,
    1: 5
}

COURSE_GROUPS = {
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

def parse_args():
    """
    @brief Parses command-line arguments for the survey filler script.
    @return Parsed arguments object with debug option.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug mode")
    return parser.parse_args()

def handle_surveys(page: Page, option: int, debug_mode: bool):
    """
    @brief Finds and handles all pending survey forms, allowing manual or automatic filling.
    @param page The Playwright page object to interact with.
    @param option The default survey response option (0-4).
    @param debug_mode Boolean flag to enable debug output.
    @return None
    """
    page.goto(CMS_SURVEYS_URL)
    page.wait_for_selector("#BodyPH_gvSurveyConducts")

    rows = page.query_selector_all("#BodyPH_gvSurveyConducts > tbody > tr")
    survey_data = extract_survey_data(rows, debug_mode)
    clear_terminal()
    for survey in survey_data:
        print(f"{survey['sr_no']}: {survey['course']} - {survey['teacher']}({survey['survey_name']})")

    custom_input = input("\nEnter the survey numbers to fill manually (comma-separated), or press Enter to fill all: ")
    custom_input = [x.strip() for x in custom_input.split(",")]

    for survey in survey_data:
        sleep(1)
        survey_url = "https://cms.bahria.edu.pk/Sys/Student/QualityAssurance/" + survey["url"]
        page.goto(survey_url)

        currently_filling = f"Filling survey: {survey['course']} - {survey['teacher']}({survey['survey_name']})"

        if survey["sr_no"] in custom_input:
            fill_custom_survey(page, currently_filling, debug_mode)
        else:
            if debug_mode:
                print(currently_filling)
            fill_survey(page, debug_mode, option)

def extract_survey_data(rows, debug_mode: bool):
    """
    @brief Extracts survey information from HTML table rows.
    @param rows List of HTML row elements containing survey data.
    @param debug_mode Boolean flag to enable debug output.
    @return List of dictionaries containing survey information.
    """
    survey_data = []
    for row in rows:
        sr_no = row.query_selector("td:nth-child(1)")
        survey_name_cell = row.query_selector("td:nth-child(3)")
        course_cell = row.query_selector("td:nth-child(4)")
        teacher_cell = row.query_selector("td:nth-child(5)")
        link = row.query_selector("td:last-child a")

        # Skip rows that aren't surveys (e.g. the single "No record found." row)
        if not course_cell or not link:
            continue

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

def get_question_groups(page: Page) -> dict:
    """
    @brief Detects which survey is loaded and returns its question groups.
    @param page The Playwright page object containing the survey form.
    @return TEACHER_GROUPS or COURSE_GROUPS.
    """
    heading_text = page.wait_for_selector("#BodyPH_surveyUserControl_lbName").inner_text()
    return TEACHER_GROUPS if "Teacher Evaluation Form" in heading_text else COURSE_GROUPS

def click_option(page: Page, group_index: int, question_number: int, option: int, debug_mode: bool):
    """
    @brief Clicks one answer of one survey question.
    Input id format: BodyPH_surveyUserControl_repeaterQuestionGroups_repeaterQuestions_{section}_rbl_{question_number}_{option}_{question_number}
    @param page The Playwright page object containing the survey form.
    @param group_index The question group (section) index.
    @param question_number The question index within the group.
    @param option The answer index to click.
    @param debug_mode Boolean flag to enable debug output.
    @return None
    """
    input_id = (
        f"BodyPH_surveyUserControl_repeaterQuestionGroups_"
        f"repeaterQuestions_{group_index}_rbl_{question_number}_{option}_{question_number}"
    )
    selector = f"#{input_id}"

    try:
        page.wait_for_selector(selector, timeout=10000)
        page.click(selector)
        if debug_mode:
            print(f"Clicked: {input_id}")
    except Exception as e:
        if debug_mode:
            print(f"Failed to click ({input_id}): {e}")

def submit_survey(page: Page, groups: dict, debug_mode: bool):
    """
    @brief Fills demographic info (course surveys only) and submits the survey.
    @param page The Playwright page object containing the survey form.
    @param groups The question groups of the loaded survey.
    @param debug_mode Boolean flag to enable debug output.
    @return None
    """
    if groups == COURSE_GROUPS:
        fill_demographic_info(page)

    submit_selector = "#BodyPH_surveyUserControl_btnSubmit"
    page.click(submit_selector)

    if debug_mode:
        print(f"Clicked: {submit_selector}")

def fill_survey(page: Page, debug_mode: bool, option: int):
    """
    @brief Automatically fills a survey form with the specified option for all questions.
    @param page The Playwright page object containing the survey form.
    @param debug_mode Boolean flag to enable debug output.
    @param option The response option to select (0=Strongly Agree, 4=Strongly Disagree).
    @return None
    """
    groups = get_question_groups(page)

    for group_index, question_count in groups.items():
        for question_number in range(question_count):
            # The attendance question (>80%) is always answered with the last option
            if question_number == 0 and group_index == 1 and groups == COURSE_GROUPS:
                click_option(page, group_index, question_number, 4, debug_mode)
            else:
                click_option(page, group_index, question_number, option, debug_mode)

    submit_survey(page, groups, debug_mode)

def fill_custom_survey(page: Page, currently_filling: str, debug_mode: bool):
    """
    @brief Lets the user answer each survey question individually.
    @param page The Playwright page object containing the survey form.
    @param currently_filling String describing which survey is being filled.
    @param debug_mode Boolean flag to enable debug output.
    @return None
    """
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
        return

    groups = get_question_groups(page)
    for group_index, question_count in groups.items():
        for question_number in range(question_count):
            question_selector = f"#BodyPH_surveyUserControl_repeaterQuestionGroups_repeaterQuestions_{group_index}_divOptions_{question_number} > label"
            question = page.query_selector(question_selector)
            if question:
                clear_terminal()
                print(currently_filling + "\n")
                print(f"Question: {question.inner_text().strip()}")
                if question_number == 0 and group_index == 1 and groups == COURSE_GROUPS:
                    selected_option = int(input(
                        "Select your answer option (0=<21%, 1=21-40%, 2=41-60%, 3=61-80%, 4=>80%): "
                    ))
                else:
                    selected_option = int(input(
                        "Select your answer option (0=Strongly Agree, 1=Agree, 2=Uncertain, 3=Disagree, 4=Strongly Disagree): "
                    ))
                click_option(page, group_index, question_number, selected_option, debug_mode)

    submit_survey(page, groups, debug_mode)

def fill_demographic_info(page: Page):
    """
    @brief Fills demographic information questions in course evaluation surveys.
    @param page The Playwright page object containing the demographic form.
    @return None
    """
    selectors = [
        # Fulltime/Parttime
        "#BodyPH_surveyUserControl_repeaterQuestionGroups_repeaterQuestions_11_rbl_0_1_0",
        # Disabled/Non-Disabled
        f"#BodyPH_surveyUserControl_repeaterQuestionGroups_repeaterQuestions_11_rbl_1_{int(not DISABLED)}_1",
        # Male/Female
        f"#BodyPH_surveyUserControl_repeaterQuestionGroups_repeaterQuestions_11_rbl_3_{GENDER}_3",
        # Age:>22/22-29/>29
        f"#BodyPH_surveyUserControl_repeaterQuestionGroups_repeaterQuestions_11_rbl_4_{AGE}_4",
        # On Campus/Off Campus
        f"#BodyPH_surveyUserControl_repeaterQuestionGroups_repeaterQuestions_11_rbl_5_{ON_CAMPUS}_5",
    ]

    for selector in selectors:
        page.wait_for_selector(selector, timeout=10000)
        page.click(selector)

if __name__ == "__main__":
    try:
        if ENROLLMENT_NUMBER == "" or PASSWORD == "" or USER_DATA_DIR == "":
            print("Error: One or more required environment variables are not set.")
            sys.exit(1)

        args = parse_args()
        context = None

        chosen_option = int(input(
            "Select your default answer option (0=Strongly Agree, 1=Agree, 2=Uncertain, 3=Disagree, 4=Strongly Disagree): "
        ))

        with sync_playwright() as p:
            try:
                # Resource blocking is off here: the survey forms are untested without their styles/scripts
                context = start_browser(p, USER_DATA_DIR, headless=not args.debug, block_resources=False)
                page = get_page(context)
                ensure_cms_login(context, page, CMS_SURVEYS_URL, args.debug)

                handle_surveys(page, chosen_option, args.debug)

                close_browser(context)
            except Exception as e:
                handle_script_error(e, context, "fillSurveys")
                sys.exit(1)

        if CHECK_UPDATES:
            check_for_updates()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)
