from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from time import sleep
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from random import uniform as random_uniform, random as random_random
from urllib.parse import urlsplit, urlunsplit
from getpass import getpass
from datetime import datetime, timedelta
import re

def init_driver(chrome_driver_path):
    # Setup Chrome options for the driver
    options = Options()
    options.add_argument("--start-maximized")  # Maximize the browser window
    options.add_argument("--incognito")  # Start Chrome in incognito mode
    options.add_argument("--disable-webrtc")  # Disable WebRTC to prevent IP leaks
    options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-devtools"])  # Disable unnecessary logging
    options.add_argument("--disable-logging")  # Further disable Chrome logging
    options.add_argument("--disable-dev-shm-usage")  # Disable shared memory to avoid errors
    options.add_argument("--disable-extensions")  # Disable Chrome extensions

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
    return driver

def find_element_by_xpath(wait, xpath):
    # Wait for an element to be present in the DOM and return it
    return wait.until(
        EC.presence_of_element_located((By.XPATH, xpath))
    )

def find_and_click(wait, xpath):
    element = wait.until(EC.element_to_be_clickable(
        (By.XPATH, xpath)))
    element.click()

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
            sleep(random_uniform(sleep_min+0.1, sleep_min+0.3))  # Add a delay between key presses to mimic typing
        element = find_element_by_xpath(wait, xpath)
    return element

def wait_for_page_load(driver):
    # Wait for the page to fully load by checking the document's readyState
    while True:
        if driver.execute_script("return document.readyState") == "complete":
            break

def scroll_to_bottom(driver):
    # Scroll to the bottom of the page to load additional content
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        # Scroll to the bottom of the page
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        # Wait for the new content to load
        sleep(2)
        
        # Calculate new scroll height and compare with the last height
        new_height = driver.execute_script("return document.body.scrollHeight")
        
        # Break the loop if no new content is loaded
        if new_height == last_height:
            break
        
        # Update the last height for the next iteration
        last_height = new_height

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

# linkedin_email = input("Please enter your LinkedIn email: ")
# linkedin_pwd = getpass("Please enter your LinkedIn password: ")
linkedin_email = "john@john-pratt.com"
linkedin_pwd = "bvVsAUnwH730g!6DZlZw"
linkedin_jobs_url = "https://www.linkedin.com/my-items/saved-jobs/?cardType=APPLIED"
linkedin_login_url = "https://www.linkedin.com/login/"
linkedin_feed_url = "https://www.linkedin.com/feed/"

# Initialize Chrome driver path for Selenium
# chrome_driver_path = input("Please download a chromedriver for Selenium to use (https://googlechromelabs.github.io/chrome-for-testing/#stable for the latest version, https://chromedriver.storage.googleapis.com/index.html for old versions). The version number must match your version of Google Chrome. Enter its file path:")
chrome_driver_path = ""
# Start LinkedIn session
driver = init_driver(chrome_driver_path)
wait = WebDriverWait(driver, 7)
driver.get(linkedin_login_url)

# Log in to LinkedIn with the provided credentials
fill_textbox(wait, "//*[@id='username'][1]", linkedin_email, sleep_min = 0, pause=False)
linkedin_pwd_ele = fill_textbox(wait, "//*[@id='password'][1]", linkedin_pwd, sleep_min = 0, pause=False)
linkedin_pwd_ele.send_keys(Keys.ENTER)

# Wait for the LinkedIn feed page to load
while True:
    current_url = driver.current_url
    if current_url == linkedin_feed_url:
        print("Page has reached the expected URL!")
        break
    sleep(1)

# Access LinkedIn certifications page
driver.get(linkedin_jobs_url)
wait_for_page_load(driver)
# stop_job_title = input("Please enter the title of the final job to include in this tracking CSV (exclusive):")
# stop_job_company = input("Please enter the Company assocaited with the final job to include in this tracking CSV (exclusive):")
stop_job_title = "Platform Engineer"
stop_job_company = "Marathon TS"

tracked_jobs = []
curr_job_title = None
curr_job_company = None
loaded_jobs_elements = find_element_by_xpath(wait, "//ul[@role='list']").find_elements(By.XPATH, "./*")
# while current job is not "stop jobs"
while not (stop_job_title == curr_job_title and stop_job_company == curr_job_company):
    # click on current job to navigate to Detail page
    for ele in loaded_jobs_elements:
        # get LI job id
        job_id = ele.find_element(By.XPATH,'./*').get_attribute("data-chameleon-result-urn").split(":")[-1]
        # go to job detail page
        curr_job_link = f"linkedin.com/jobs/view/{job_id}"
        driver.execute_script(f"window.open('https://{curr_job_link}', '_blank');")
        driver.switch_to.window(driver.window_handles[-1])
        # 
        curr_job_title = find_element_by_xpath(wait, "(//h1)[1]").text
        curr_job_applied_time_ago = find_element_by_xpath(wait, "//span[@class='post-apply-timeline__entity-time']").text
        curr_job_company = find_element_by_xpath(wait, "(//a)[10]").text
        curr_job_contact1, curr_job_contact2 = "", ""
        
        # only try finding contacts if their expected parent element is present
        # TODO make this business logic more complex so it can instantly tell if there is no Person's full name listed under this section
        if (len(driver.find_elements(By.XPATH, '//h2[@class="text-heading-large" and text()="People you can reach out to"]')) > 0):
            try:
                curr_job_contact1 = find_element_by_xpath(wait, "(//div[contains(@class, 'job-details-people-who-can')])[3]//strong").text
                curr_job_contact2 = find_element_by_xpath(wait, "//div[@class='job-details-people-who-can-help__section']//strong").text
            except Exception:
                print("Found no 'job contacts' for this job")
                pass

        find_and_click(wait, '//button[@aria-label="Click to see more description"]')
        find_element_by_xpath(wait, "//button[@aria-label='Click to see less description']")
        curr_job_desc_elements = find_element_by_xpath(wait, "(//div[contains(@class, 'jobs-box__html-content')]/*)[2]/*/*").find_elements(By.XPATH, "./*")
        curr_job_description = ""

        for job_desc_ele in curr_job_desc_elements:
            curr_job_description += (job_desc_ele.text + "\n")
        
        tracked_jobs.append({
            "company" : curr_job_company,
            "job_title" : curr_job_title,
            "date_applied" : get_past_date(curr_job_applied_time_ago),
            "job_posting" : curr_job_link,
            "JD" : curr_job_description
        })
        # close new tab, go back to old one
        driver.close()
        print(tracked_jobs[-1])

print(tracked_jobs)

# Locate the element containing certifications
div_ele = find_element_by_xpath(wait, wait, "//div[contains(@class, 'scaffold-finite-scroll__content')]")
ul_ele = div_ele.find_element(By.TAG_NAME, 'ul')
cert_li_eles = ul_ele.find_elements(By.XPATH, './li')  # Find all certifications

# Process certifications
print(f"Certs found on LinkedIn profile: {len(cert_li_eles)}")
full_certs = []


print(f"ERROR : Failed to add the following certs - {[d['cert_name'] for d in failures]}. Go back & add these manually.")

print("Finished entering all certifications. *IMPORTANT*: You will have to go back & enter dates (day of month) manually.")
print("Please validate that no extra certifications were added in error.")
input("Press any key to exit: ")
