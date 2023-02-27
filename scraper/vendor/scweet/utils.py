import random

import chromedriver_autoinstaller

from time import sleep
from typing import Generator, Literal, Optional

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from common.logging import logger
from vendor.scweet.credentials import Credentials


def init_driver(headless=True, proxy=None, option=None, profile_dir: Optional[str] = None, user_data_dir: Optional[str] = None):
    """ initiate a chromedriver or firefoxdriver instance
        --option : other option to add (str)
    """

    options = ChromeOptions()
    driver_path = chromedriver_autoinstaller.install()

    if headless is True:
        logger.debug("chrome: launching in headless mode.")
        options.add_argument('--disable-gpu')
        options.headless = True
    else:
        options.headless = False
    options.add_argument('log-level=3')
    if proxy is not None:
        options.add_argument('--proxy-server=%s' % proxy)
        logger.debug(f'chrome: using proxy : {proxy}')
    # if show_images == False:
    #     prefs = {"profile.managed_default_content_settings.images": 2}
    #     options.add_experimental_option("prefs", prefs)
    if option is not None:
        options.add_argument(option)
    if profile_dir is not None:
        options.add_argument(f'--profile-director={profile_dir}')
    if user_data_dir is not None:
        options.add_argument(f'--user-data-dir={user_data_dir}')

    driver = webdriver.Chrome(options=options, executable_path=driver_path)
    driver.set_page_load_timeout(100)

    return driver


def wait_for_element(driver: webdriver.Remote, xpath: str, timeout=30) -> WebElement:
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, xpath)))


def wait_for_twitter_load(driver: webdriver.Remote, url: Optional[str] = None):
    if url is not None:
        logger.debug(f'going to url {url}')
        driver.get(url)
    elif 'twitter' not in driver.current_url:
        logger.debug('going to twitter home')
        driver.get('https://twitter.com')
    wait_for_element(driver, '//a[contains(@aria-label, "Twitter")]')


def needs_login(driver: webdriver.Remote) -> bool:
    return check_exists_by_xpath(driver=driver, xpath='//a[@href="/login"]')


def log_in_if_required(driver: webdriver.Remote, credentials: Credentials, timeout=20, wait=4, force=False):
    wait_for_twitter_load(driver)

    if not needs_login(driver) and not force:
        logger.debug('skipping login (not needed)')
        return
    logger.debug('needs login!')

    # FYI: this page doesn't have the twitter home link on it, so
    # wait_for_twitter_load doesn't work (but is unnecessary anyway as we use
    # the form wait instead)
    driver.get('https://twitter.com/i/flow/login')

    normal_username_xpath = '//input[@autocomplete="username"]'
    password_xpath = '//input[@autocomplete="current-password"]'
    username_xpath = '//input[@data-testid="ocfEnterTextTextInput"]'

    sleep(random.uniform(wait, wait + 1))
    logger.debug('getting form')

    # enter email
    username_input = wait_for_element(driver, normal_username_xpath)
    sleep(random.uniform(wait, wait + 1))
    username_input.send_keys(credentials.username)
    sleep(random.uniform(wait, wait + 1))
    username_input.send_keys(Keys.RETURN)
    sleep(random.uniform(wait, wait + 1))

    # in case twitter spotted unusual login activity : enter your username
    if check_exists_by_xpath(username_xpath, driver):
        raise Exception('UNUSUAL SHIT!!!!')

    # enter password
    password_el = wait_for_element(driver, password_xpath)
    password_el.send_keys(credentials.password)

    logger.debug('login info entered')
    sleep(random.uniform(wait, wait + 1))
    password_el.send_keys(Keys.RETURN)
    sleep(random.uniform(wait, wait + 1))


# TODO: wait for loading spinner to stop?
def get_follow(driver: webdriver.Remote, username: str, headless: bool, credentials: Credentials, follow: Literal['following', 'followers'] = None, verbose=1, wait=2, limit=float('inf')) -> Generator[str, None, None]:
    """ get the following or followers of a list of users """
    wait_for_twitter_load(driver)
    sleep(wait)  # TODO: need to wait for the timeline to load too..?
    log_in_if_required(driver, credentials, wait=wait)

    logger.info(f'crawling {username} {follow}')
    # navigate to the profile first - pretend you're real!
    wait_for_twitter_load(driver, url='https://twitter.com/' + username)
    sleep(random.uniform(wait - 0.5, wait + 0.5))
    wait_for_twitter_load(
        driver, url='https://twitter.com/' + username + '/' + follow)
    sleep(random.uniform(wait - 0.5, wait + 0.5))

    # check if we must keep scrolling
    scrolling = True
    last_position = driver.execute_script("return window.pageYOffset;")
    seen_usernames = set()
    while scrolling:
        # get the card of following or followers
        # this is the primaryColumn attribute that contains both followings and followers
        primaryColumn = driver.find_element(
            by=By.XPATH, value='//div[contains(@data-testid,"primaryColumn")]')
        # extract only the Usercell
        page_cards = primaryColumn.find_elements(
            by=By.XPATH, value='//div[contains(@data-testid,"UserCell")]')
        for card in page_cards:
            # get the following or followers element
            element = card.find_element(
                by=By.XPATH, value='.//div[1]/div[1]/div[1]//a[1]')
            follow_profile_href = str(element.get_attribute('href'))
            follow_username = follow_profile_href.split('/')[-1]
            if follow_username not in seen_usernames:
                seen_usernames.add(follow_username)
                yield follow_username
            if len(seen_usernames) >= limit:
                return

        scroll_attempt = 0
        while True:
            sleep(random.uniform(wait - 0.5, wait + 0.5))
            driver.execute_script(
                'window.scrollTo(0, document.body.scrollHeight);')
            sleep(random.uniform(wait - 0.5, wait + 0.5))
            curr_position = driver.execute_script(
                "return window.pageYOffset;")
            if last_position == curr_position:
                scroll_attempt += 1
                # end of scroll region
                if scroll_attempt >= 2:
                    # nothing more to load!
                    return
                else:
                    # attempt another scroll
                    sleep(random.uniform(wait - 0.5, wait + 0.5))
            else:
                last_position = curr_position
                break


def check_exists_by_xpath(xpath: str, driver: webdriver.Remote) -> bool:
    try:
        driver.find_element(by=By.XPATH, value=xpath)
    except NoSuchElementException:
        return False
    return True


# if the login fails, find the new log in button and log in again.
# if check_exists_by_link_text("Log in", driver):
#     print("Login failed. Retry...")
#     login = driver.find_element_by_link_text("Log in")
#     sleep(random.uniform(wait - 0.5, wait + 0.5))
#     driver.execute_script("arguments[0].click();", login)
#     sleep(random.uniform(wait - 0.5, wait + 0.5))
#     sleep(wait)
#     log_in_if_required(driver, credentials, force=True)
#     sleep(wait)
# # case 2
# if check_exists_by_xpath('//input[@name="session[username_or_email]"]', driver):
#     print("Login failed. Retry...")
#     sleep(wait)
#     log_in_if_required(driver, credentials, force=True)
#     sleep(wait)
