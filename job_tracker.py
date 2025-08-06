# import undetected_chromedriver as uc

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from time import sleep
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from random import uniform as random_uniform, random as random_random
from urllib.parse import urlsplit, urlunsplit
from getpass import getpass
from datetime import datetime, timedelta
import os
import re
from csv import writer
from dotenv import load_dotenv

js_click_indicator = """
function showClickIndicator(x, y, offsetX = 0, offsetY = 0) {
    var clickIndicator = document.createElement('div');
    clickIndicator.style.position = 'absolute';
    clickIndicator.style.left = (x - offsetX) + 'px';  // Adjust by iframe's offset
    clickIndicator.style.top = (y - offsetY) + 'px';   // Adjust by iframe's offset
    clickIndicator.style.width = '10px';
    clickIndicator.style.height = '10px';
    clickIndicator.style.backgroundColor = 'red';
    clickIndicator.style.borderRadius = '50%';
    clickIndicator.style.zIndex = '10000';
    document.body.appendChild(clickIndicator);

    setTimeout(function() {
        clickIndicator.remove();
    }, 100);
}
showClickIndicator(arguments[0], arguments[1], arguments[2], arguments[3]);
"""

## TODO store xpaths for repeat elements on page as variables

def init_driver(chrome_driver_path):
    # Setup Chrome options for the driver
    options = Options()

    options.add_argument('--no-sandbox')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument("--start-maximized")  # Maximize the browser window
    options.add_argument("--incognito")  # Start Chrome in incognito mode
    options.add_argument("--disable-webrtc")  # Disable WebRTC to prevent IP leaks
    options.add_argument('--handle_prefs') # This step is dedicated to the undetected_chromedriver
    options.add_argument("--disable-popup-blocking")
    # options.add_experimental_option("prefs", prefs)
    # options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-devtools"])  # Disable unnecessary logging
    options.add_argument("--disable-logging")  # Further disable Chrome logging
    options.add_argument("--disable-dev-shm-usage")  # Disable shared memory to avoid errors
    options.add_argument("--disable-extensions")  # Disable Chrome extensions

    # add real user agent so webdriver appears more human-like
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ...")

    # use a chrome profile to make browser appear more human-like
    profile_path = os.path.abspath("./chrome_profile")
    options.add_argument(f"user-data-dir={profile_path}")

    # start browser with semi-random window size, to appear more human-like
    s = random_uniform(0.5, (1/3)**0.5)
    w, h = int(3840 * s), int(2160 * s)
    options.add_argument(f"--window-size={w},{h}")

    # Disable WebRTC IP handling to ensure no leaks
    options.add_experimental_option("prefs", {
        "webrtc.ip_handling_policy": "disable_non_proxied_udp"
    })

    # Provide a default chromedriver path if not specified
    if not chrome_driver_path:
        print("No path to chromedriver provided. Using default...")
        chrome_driver_path= './chromedriver'

    # Initialize the Chrome webdriver with the provided path and options
    service = Service(chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
            })
        """
    })

    # driver = uc.Chrome(options=options)
    return driver

def find_element_by_xpath(wait, xpath, attempts=30, delay=0.1):
    """
    Retry wrapper that finds an element by XPath with retries if it becomes stale.
    """
    for _ in range(attempts):
        try:
            return wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
        except StaleElementReferenceException:
            time.sleep(delay)

    raise StaleElementReferenceException(f"Element with XPath '{xpath}' remained stale after {attempts} attempts.")

def find_and_click_element_with_offset(element, offset_x_pct, offset_y_pct):
    # print(element.get_attribute('outerHTML'))
    if offset_x_pct < 0 or offset_x_pct > 1:
        print("offset_x_pct for find_and_click_with_offset must be between 0 and 1.")
        raise MoveTargetOutOfBoundsException
    if offset_y_pct < 0 or offset_y_pct > 1:
        print("offset_y_pct for find_and_click_with_offset must be between 0 and 1.")
        raise MoveTargetOutOfBoundsException
    
    actions = ActionChains(driver)

    # Calculate the initial offset_x based on the percentage
    initial_offset_x = int(element.size['width'] * offset_x_pct)
    # Ensure offset_x is at least 1 and at most element.size['width'] - 1
    offset_x = max(1, min(initial_offset_x, element.size['width'] - 1))
    # Calculate the initial offset_y based on the percentage
    initial_offset_y = int(element.size['height'] * offset_x_pct)
    # Ensure offset_y is at least 1 and at most element.size['height'] - 1
    offset_y = max(1, min(initial_offset_y, element.size['height'] - 1))

    # Perform the click and hold action, after moving to a random part of element
    actions.move_to_element_with_offset(element, offset_x, offset_y)
    click_location = (element.location['x'] + offset_x, \
                      element.location['y'] + offset_y, )
    
    driver.execute_script(js_click_indicator, *click_location)
    actions.click_and_hold().perform()

    # Generate a random duration for the hold
    sleep(random_uniform(0.05, 0.2))

    # Release the mouse click
    actions.release()
    actions.perform()
    sleep(random_uniform(0.05, 0.1))
    
    return element

def find_and_click_with_offset(wait, xpath, offset_x_pct, offset_y_pct):
    element = wait.until(EC.element_to_be_clickable(
        (By.XPATH, xpath)))
    element = find_and_click_element_with_offset(element, offset_x_pct, offset_y_pct)
    sleep(random_uniform(0.2, 0.4))
    return element

def find_and_click(wait, xpath):
    # wait for element to be "clickable"
    element = wait.until(EC.element_to_be_clickable(
        (By.XPATH, xpath)))

    # Calculate random coordinates within the element's dimensions
    random_x_pct = random_uniform(0, 0.5)
    random_y_pct = random_uniform(0, 0.5)
    sleep(random_uniform(0.2, 0.4))
    return find_and_click_with_offset(wait, xpath, random_x_pct, random_y_pct)

def fill_textbox_immediate(wait, xpath, input, clear = True):
    # Find the element and optionally clear the input before filling it
    element = find_element_by_xpath(wait, xpath)
    if clear:
        element.clear()  # Clear any existing value in the textbox
    element.send_keys(input)
    return element

def fill_textbox(wait, xpath, input, sleep_min = 0, pause = True):
    # Slowly fill the textbox character by character to simulate human input
    element = find_element_by_xpath(wait, xpath)
    
    for char in input:
        element.send_keys(char)
        if pause:
            sleeptime = random_uniform(sleep_min+0.1, sleep_min+0.3)
            sleep(sleeptime)  # Add a delay between key presses to mimic typing
            # print(f"slept for {sleeptime} seconds between keystrokes")
        element = find_element_by_xpath(wait, xpath)
    return element

def wait_for_page_load(driver):
    # Wait for the page to fully load by checking the document's readyState
    while True:
        if driver.execute_script("return document.readyState") == "complete":
            break

def get_all_descendant_text(el):
    """
    Recursively collects .text from all child/grandchild/etc elements of `el`.
    Returns a single string with each piece of text concatenated.
    """
    texts = []
    # get direct children
    children = el.find_elements(By.XPATH, "./*")
    for child in children:
        # add this child's own text
        texts.append(child.text or "")
        # recurse into its children
        texts.append(get_all_descendant_text(child))
    return " ".join(texts)

def get_past_date(time_str):
    now = datetime.now()

    # Regex to extract number and unit
    match = re.match(r"(\d+)\s+(minute|minutes|hour|hours|day|days)\s+ago", time_str.strip().lower())
    if not match:
        raise ValueError("Invalid time string format")

    value, unit = int(match.group(1)), match.group(2)

    if "minute" in unit:
        delta = timedelta(minutes=value)
    elif "hour" in unit:
        delta = timedelta(hours=value)
    elif "day" in unit:
        delta = timedelta(days=value)
    else:
        raise ValueError("Unsupported time unit")

    past_date = now - delta
    return past_date.strftime("%-m/%-d/%Y")  # For Unix-like systems
    # return past_date.strftime("%#m/%#d/%Y")  # Use this line instead on Windows

def write_jobs_to_csv(jobs_list, filename, writemode="a"):
    """
    Write a list of job entries (dicts) to a CSV file where:
    - 1st column: "company"
    - 2nd column: empty
    - 3rd column: "job_title"
    - 4th column: "contacts"
    - 5th column: empty
    - 6th column: "date_applied"
    - 7th column: "job_link"
    - 8th column: "job_description"
    
    :param jobs_list: List of dicts, each containing keys:
                      'company', 'job_title', 'contacts',
                      'date_applied', 'job_link', 'job_description'
    :param filename:   Output CSV filename (e.g., "jobs.csv")
    """
    headers = ['company', 'staffing company', 'job_title', 'contacts', 'status', 'date_of_last_contact', 'date_applied', 'job_link', 'job_description']
    
    with open(filename, writemode, newline='', encoding='utf-8') as csvfile:
        csv_writer = writer(csvfile)
        if writemode == "w":
            csv_writer.writerow(headers)
                    
        for job in jobs_list:
            row = [
                job.get('company', ''),
                '',
                job.get('job_title', ''),
                job.get('contacts', ''),
                '',
                job.get('date_applied', ''),
                job.get('date_applied', ''),
                job.get('job_link', ''),
                job.get('job_description', '')
            ]
            csv_writer.writerow(row)

load_dotenv()

linkedin_email = os.getenv("LINKEDIN_EMAIL") or input("Please enter your LinkedIn email: ")
linkedin_pwd = os.getenv("LINKEDIN_PWD") or getpass("Please enter your LinkedIn password: ")

if os.getenv("LINKEDIN_EMAIL"):
    print(f"Pre-filled LI email: {linkedin_email}")

linkedin_jobs_url = "https://www.linkedin.com/my-items/saved-jobs/?cardType=APPLIED"
linkedin_login_url = "https://www.linkedin.com/login/"
linkedin_feed_url = "https://www.linkedin.com/feed/"

# Initialize Chrome driver path for Selenium
# chrome_driver_path = input("Please download a chromedriver for Selenium to use (https://googlechromelabs.github.io/chrome-for-testing/#stable for the latest version, https://chromedriver.storage.googleapis.com/index.html for old versions). The version number must match your version of Google Chrome. Enter its file path:")
chrome_driver_path = ""
# Start LinkedIn session
driver = init_driver(chrome_driver_path)
wait = WebDriverWait(driver, 7)
driver.get(linkedin_jobs_url)
wait_for_page_load(driver)

# if we need to,
if "login" in driver.current_url:
    # Log in to LinkedIn with the provided credentials
    fill_textbox(wait, "//*[@id='username'][1]", linkedin_email, sleep_min = 0.2, pause=False)
    linkedin_pwd_ele = fill_textbox(wait, "//*[@id='password'][1]", linkedin_pwd, sleep_min = 0, pause=True)
    linkedin_pwd_ele.send_keys(Keys.ENTER)

    # Wait for the LinkedIn feed page to load
    while True:
        current_url = driver.current_url
        if current_url == linkedin_jobs_url:
            print("Page has reached the expected URL!")
            break
        sleep(1)

# Access LinkedIn Applied Jobs page
print("Waiting for job list page to load...")
wait_for_page_load(driver)
stop_job_title = os.getenv("STOP_JOB_TITLE") or input("Please enter the title of the final job to include in this tracking CSV (exclusive):")
stop_job_company = os.getenv("STOP_JOB_COMPANY") or input("Please enter the Company of the final job to include in this tracking CSV (exclusive):")
print("Successfully loaded Stop Job details!")

tracked_jobs = []
# start blank file
write_jobs_to_csv(tracked_jobs, "job_list.csv", writemode="w")

curr_job_title = ""
curr_job_company = ""

## TODO add business logic for Start Job - don't always start from most recently applied job
# start_job_title = os.getenv("START_JOB_TITLE") or input("Please enter the Title of the *first* job to include in this tracking CSV (exclusive):")
# start_job_company = os.getenv("START_JOB_COMPANY") or input("Please enter the Company of the final job to include in this tracking CSV (exclusive):")

# start_job_found = False
# start_job_found = True
# while current job is not "stop jobs"
while not (stop_job_title.strip() == curr_job_title.strip() and stop_job_company.strip() == curr_job_company.strip()):
    print(f"Attempting to load all Job elements on Job List page...")
    loaded_jobs_elements = find_element_by_xpath(wait, "//ul[@role='list']").find_elements(By.XPATH, "./*")
    print(f"All Job elements on Job List page loaded!")
    # "quick & dirty" search through all jobs on current page until we find "start" job
    
    # for ele in loaded_jobs_elements:
    #     job_txt = get_all_descendant_text(ele)
    #     if start_job_title in job_txt and start_job_company in job_txt:
    #         start_job_found = True

    # if start_job_found:
    # click on current job to navigate to Detail page
    for ele in loaded_jobs_elements:

        # get LI job id
        job_id = ele.find_element(By.XPATH,'./*').get_attribute("data-chameleon-result-urn").split(":")[-1]
        # go to job detail page
        curr_job_link = f"linkedin.com/jobs/view/{job_id}"
        driver.execute_script(f"window.open('https://{curr_job_link}', '_blank');")
        driver.switch_to.window(driver.window_handles[-1])
        
        # wait indefinitely for job page to load before trying to parse it 
        wait_for_page_load(driver)
        curr_job_title = find_element_by_xpath(wait, "(//h1)[1]").text
        curr_job_company = find_element_by_xpath(wait, "(//a)[10]").text
        
        print(f"Parsing \"{curr_job_title}\" at \"{curr_job_company}\"...")
        
        curr_job_applied_time_ago = find_element_by_xpath(wait, "//span[@class='post-apply-timeline__entity-time']").text
        
        curr_job_contact1, curr_job_contact2 = "", ""
        
        # only try finding contacts if their expected parent element is present
        # TODO make this business logic more complex so it can instantly tell if there is no Person's full name listed under this section

        ## Seems like "See more" button indicates
        if (len(driver.find_elements(By.XPATH, '//h2[@class="text-heading-large" and text()="People you can reach out to"]')) > 0):
            try:
                curr_job_contact1 = find_element_by_xpath(wait, "(//div[contains(@class, 'job-details-people-who-can')])[3]//strong").text
                curr_job_contact2 = find_element_by_xpath(wait, "//div[@class='job-details-people-who-can-help__section']//strong").text
            except Exception:
                print("Found no 'job contacts' for this job")
                pass

        ## TODO only try clicking on this element if it's present
        see_more_btn_xpath = "//button[contains(@aria-label, 'see more')]"
        # if find_element_by_xpath()
        find_and_click(wait, see_more_btn_xpath)

        ## This needs to be dynamic depending on which type of "job description elements" are present on the page
        curr_job_desc_elements = None
        curr_job_description = ""
        curr_job_desc_elements = find_element_by_xpath(wait, "//div[contains(@class, 'jobs-box__html-content')]")
        curr_job_description = get_all_descendant_text(curr_job_desc_elements)  
        
        tracked_jobs.append({
            "company" : curr_job_company,
            "job_title" : curr_job_title,
            "contacts" : f"{curr_job_contact1}, {curr_job_contact2}" if curr_job_contact1 or curr_job_contact2 else "",
            "date_applied" : get_past_date(curr_job_applied_time_ago),
            "job_link" : curr_job_link,
            "job_description" : curr_job_description
        })
        # log current job to CSV to minimize data loss, we can remove tracked_jobs as master list later if desired..
        write_jobs_to_csv(tracked_jobs[-1:], "job_list.csv", writemode="a")

        # close new tab, go back to old one
        driver.close()
        main_handle = driver.window_handles[0]
        driver.switch_to.window(main_handle)

        # break for loop if Stop Job was found:
        if (stop_job_title.strip() == curr_job_title.strip() and stop_job_company.strip() == curr_job_company.strip()):
            break
    # click to next page of jobs
    find_and_click(wait, '//button[@aria-label="Next"]')

print(tracked_jobs)

# Process scraped jobs
# write_jobs_to_csv(tracked_jobs, "job_list.csv")


print("Finished entering all certifications. *IMPORTANT*: You will have to go back & enter dates (day of month) manually.")
print("Please validate that no extra certifications were added in error.")
input("Press any key to exit: ")
