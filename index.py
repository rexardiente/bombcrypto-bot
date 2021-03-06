# -*- coding: utf-8 -*-
from cv2 import cv2
from os import listdir
from random import random, randint
import numpy as np
import mss
import pyautogui
import time
from tqdm import tqdm
import platform
import yaml
from screeninfo import get_monitors
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

# Load config file.
SYSTEM_PATH = "PATH/bombcrypto-bot"
stream = open("{}/config.yaml".format(SYSTEM_PATH), 'r')
c = yaml.safe_load(stream)
ct = c['threshold']
xt = c['extension']
wl = c['wallet']
time_intervals = c['time_intervals']
pause = time_intervals['movements_interval']
round_robin_scheduler = time_intervals['round_robin_scheduler']
go_work_all_scheduler = time_intervals['go_work_all_scheduler']
pyautogui.PAUSE = pause


def system_screen_size():
    monitor = get_monitors()[0]
    return [monitor.width, monitor.height]


def print_screen():
    with mss.mss() as sct:
        # monitor = sct.monitors[0]
        # The screen part to capture
        screenshotting = system_screen_size()
        monitor = {"top": 0, "left": 0, "width": screenshotting[0], "height": screenshotting[1]}
        sct_img = np.array(sct.grab(monitor))
        # Grab the data
        return sct_img[:, :, :3]


def positions(target, threshold=ct['default'], img=None):
    if img is None:
        img = print_screen()

    result = cv2.matchTemplate(img, target, cv2.TM_CCOEFF_NORMED)
    w = target.shape[1]
    h = target.shape[0]

    yloc, xloc = np.where(result >= threshold)

    rectangles = []
    for (x, y) in zip(xloc, yloc):
        rectangles.append([int(x), int(y), int(w), int(h)])
        rectangles.append([int(x), int(y), int(w), int(h)])

    rectangles, weights = cv2.groupRectangles(rectangles, 1, 0.2)
    return rectangles


def add_randomness(n, randomn_factor_size=None):
    """Returns n with randomness
    Parameters:
        n (int): A decimal integer
        randomn_factor_size (int): The maximum value+- of randomness that will be
            added to n

    Returns:
        int: n with randomness
    """

    if randomn_factor_size is None:
        randomness_percentage = 0.1
        randomn_factor_size = randomness_percentage * n

    random_factor = 2 * random() * randomn_factor_size
    if random_factor > 5:
        random_factor = 5
    without_average_random_factor = n - randomn_factor_size
    randomized_n = int(without_average_random_factor + random_factor)
    # logger('{} with randomness -> {}'.format(int(n), randomized_n))
    return int(randomized_n)


def random_move(x, y, t, to_right=0, to_up=0):
    # pyautogui.moveTo(x + to_right, y + to_up, t / 1)
    pyautogui.moveTo(add_randomness(x + to_right, 10), add_randomness(y + to_up, 10), t + random() / 2)


def click_button(img, position='left', timeout=3, threshold=ct['default']):
    # logger(None, progress_indicator=True)
    start = time.time()
    has_timed_out = False
    while not has_timed_out:
        matches = positions(img, threshold=threshold)

        if len(matches) == 0:
            has_timed_out = time.time() - start > timeout
            continue

        x, y, w, h = matches[0]
        pos_click_x = x + w / 2
        pos_click_y = y + h / 2
        random_move(pos_click_x, pos_click_y, 1)
        # default is 'left', 'middle', or 'right'.
        # ie: pyautogui.click(button='left')
        pyautogui.click(button=position)
        return True

    return False


def is_image_exists(img, timeout=3, threshold=ct['default']):
    # logger(None, progress_indicator=True)
    start = time.time()
    has_timed_out = False
    while not has_timed_out:
        matches = positions(img, threshold=threshold)

        if len(matches) == 0:
            has_timed_out = time.time() - start > timeout
            continue
        # return true if image has been found
        return True
    # return false if no image found on the screen
    return False


def remove_suffix(input_string, suffix):
    """Returns the input_string without the suffix"""
    if suffix and input_string.endswith(suffix):
        return input_string[:-len(suffix)]
    return input_string


def load_images(dir_path='{}/targets/'.format(SYSTEM_PATH)):
    """ Programatically loads all images of dir_path as a key:value where the
        key is the file name without the .png suffix
        Returns: dict: dictionary containing the loaded images as key:value pairs.
    """
    file_names = listdir(dir_path)
    targets = {}
    for file in file_names:
        path = '{}/targets/'.format(SYSTEM_PATH) + file
        targets[remove_suffix(file, '.png')] = cv2.imread(path)

    return targets


def init_wallet(private_key, is_sub_account):
    while True:
        try:
            # Login metamask on first load..
            chrome_options = Options()
            chrome_options.add_extension(xt['PATH'])
            # set browser in full screen
            chrome_options.add_argument('start-maximized')
            chrome_options.add_experimental_option("useAutomationExtension", False)
            # enable for browser to stay open, even selenium is finished
            chrome_options.add_experimental_option("detach", True)
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            driver.implicitly_wait(20)

            wait = WebDriverWait(driver, 20)
            # wait all 2 windows are loaded
            wait.until(EC.number_of_windows_to_be(2))
            # remove empty tab and use the wallet tab
            try:
                driver.switch_to.window(driver.window_handles[1])
                driver.close()
            finally:
                wait.until(EC.number_of_windows_to_be(1))
                driver.switch_to.window(driver.window_handles[0])

            # wait until the extension has loaded.
            wait.until(EC.presence_of_element_located((By.XPATH, '//button[text()="Get Started"]'))).click()
            wait.until(EC.presence_of_element_located((By.XPATH, '//button[text()="Import wallet"]'))).click()
            wait.until(EC.presence_of_element_located((By.XPATH, '//button[text()="No Thanks"]'))).click()
            # After this you will need to enter you wallet details
            inputs = wait.until(EC.presence_of_all_elements_located((By.XPATH, '//input')))
            # inputs = driver.find_elements(By.XPATH, '//input')
            inputs[0].send_keys(wl['SECRET_RECOVERY_PHRASE'])
            inputs[1].send_keys(wl['NEW_PASSWORD'])
            inputs[2].send_keys(wl['NEW_PASSWORD'])

            wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'first-time-flow__terms'))).click()
            wait.until(EC.presence_of_element_located((By.XPATH, '//button[text()="Import"]'))).click()
            wait.until(EC.presence_of_element_located((By.XPATH, '//button[text()="All Done"]'))).click()
            # close pop up dialog box
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'popover-header__button'))).click()
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'network-display--clickable'))).click()
            # Add custom network into metamask wallet
            wait.until(EC.presence_of_element_located((By.XPATH, '//button[text()="Add Network"]'))).click()

            # Add network form fields
            inputs = wait.until(EC.presence_of_all_elements_located((By.XPATH, '//input')))
            inputs[0].send_keys(wl['network_name'])
            inputs[1].send_keys(wl['rpc_url'])
            inputs[2].send_keys(wl['chain_id'])
            inputs[3].send_keys(wl['symbol'])
            inputs[4].send_keys(wl['block_exp_url'])

            # save new network
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'btn-primary'))).click()
            # make sure drivers are loaded
            # driver.implicitly_wait(20)
            time.sleep(2)
            #  if not the owner then import new private key and change wallet account
            if is_sub_account:
                # point the cursor into network button
                # then add # to make it pointed into accounts button
                accounts_tab = positions(images['networks_tab'], threshold=0.7)
                for (x, y, w, h) in accounts_tab:
                    random_move(x + (w / 2), y + (h / 2), 1, to_right=100)
                    pyautogui.click()
                time.sleep(0.5)
                # import wallet process
                import_acc = positions(images['import_account'], threshold=0.7)
                for (ix, iy, iw, ih) in import_acc:
                    random_move(ix + (iw / 2), iy + (ih / 2), 1)
                    pyautogui.click()
                time.sleep(0.5)
                # input sub_account private key
                inputs = wait.until(EC.presence_of_all_elements_located((By.XPATH, '//input')))
                inputs[0].send_keys(private_key)
                # submit new account
                import_button = positions(images['import_account_button'], threshold=0.7)
                for (kx, ky, kw, kh) in import_button:
                    random_move(kx + (kw / 2), ky + (kh / 2), 1)
                    pyautogui.click()
                time.sleep(0.5)

            # open game landing page in new tab, and set the game ready to play
            driver.execute_script('''window.open("https://app.bombcrypto.io/","_blank");''')
            driver.switch_to.window(driver.window_handles[1])
            wait.until(EC.number_of_windows_to_be(2))
            # remove empty tab and use the wallet tab
            try:
                driver.switch_to.window(driver.window_handles[0])
                driver.close()
            finally:
                wait.until(EC.number_of_windows_to_be(1))
                driver.switch_to.window(driver.window_handles[0])

            print("Done to load extension")
            return False
        except Exception:
            print("Failed to load extension, Please close that browser manually")


def automate_gameplay():
    # Terms and service process
    if is_image_exists(images['terms-and-service'], timeout=10):
        if click_button(images['terms-and-service-checkbox'], timeout=10):
            click_button(images['terms-and-service-accept'], timeout=10)
    else:
        pass
    # click connect wallet button
    if click_button(images['connect-wallet'], timeout=10):
        print('???? Connect wallet button detected, logging in!')

    # newly created account
    if click_button(images['btn-next'], timeout=10):
        if click_button(images['btn-connect'], timeout=10):
            pass
    # sometimes signup popup won't show fast
    time.sleep(2)
    if click_button(images['select-wallet-2'], timeout=10):
        pass
    if click_button(images['hero-icon'], timeout=10):
        pass
    if click_button(images['go-rest-all'], timeout=10):
        pass
    if click_button(images['go-work-all'], timeout=10):
        pass
    # return to home page to start game
    if click_button(images['x'], timeout=10):
        if click_button(images['treasure-hunt-icon'], timeout=10):
            pass


def set_all_work():
    print("Setting all characters to go back to work!!!")
    if click_button(images['go-back-arrow'], timeout=10):
        print('Back to home page')
        if click_button(images['hero-icon'], timeout=10):
            pass
        if click_button(images['go-rest-all'], timeout=10):
            pass
        if click_button(images['go-work-all'], timeout=10):
            pass
        # return to home page to start game
        if click_button(images['x'], timeout=10):
            if click_button(images['treasure-hunt-icon'], timeout=10):
                pass


# avoid game idle
def avoid_game_idle():
    if click_button(images['go-back-arrow'], timeout=10):
        print('Back to home page')
        time.sleep(1)
        if click_button(images['hero-icon'], timeout=10):
            pass
        if click_button(images['x'], timeout=10):
            if click_button(images['treasure-hunt-icon'], timeout=10):
                pass


def round_robin_clicker():
    print("round_robin_clicker...")
    global scheduler
    current_timestamp = int(time.time())
    # track all available browsers
    browser = positions(images[os_browser], threshold=0.9)
    for (x, y, w, h) in browser:
        random_move(x + (w / 2), y + (h / 2), 1)
        pyautogui.click()
        avoid_game_idle()
        # Set back all characters to work if 15 minutes has passed based on scheduler
        if current_timestamp >= scheduler:
            set_all_work()
        # screen_size = system_screen_size()
        # width = screen_size[0]
        # height = screen_size[1]
        # # move the cursor on the page randomly
        # for counts in range(0, 3):
        #     click_button(images['key_to_click'], timeout=10)
        #     rand_width_loc = randint(20, width - 20)
        #     rand_height_loc = randint(20, height - 20)
        #     random_move(rand_width_loc, rand_height_loc, 1)
    # make sure to update scheduler if needed
    if current_timestamp >= scheduler:
        scheduler = current_timestamp + (60 * go_work_all_scheduler)


def main():
    global images
    global os_browser
    global accounts  # array of private keys
    global scheduler  # timestamp format

    images = load_images()
    # browser count will based on this value.
    accounts = wl['accounts']

    # load type of browser icon based on OS
    current_platform = platform.system().lower()
    if current_platform == "linux" or current_platform == "linux2":
        os_browser = "linux-chrome"
    elif current_platform == "darwin":
        os_browser = "macos-chrome"
    else:
        os_browser = "windows-chrome"

    # initialize browsers and wallet based on the accounts count
    for x in range(0, len(accounts)):
        # check if account is the owner of the pass phrase
        if not x == 0:
            init_wallet(accounts[x], True)
        # load default wallet
        else:
            init_wallet(accounts[x], False)
    # after setting up all browsers
    # set delay if only has less than 2 accounts
    if len(accounts) > 2:
        time.sleep(5)
    else:
        time.sleep(10)

    # track all open Google Chrome browser, and iterate each one.
    browser = positions(images[os_browser], threshold=0.9)
    for (x, y, w, h) in browser:
        # place the cursor into the browser icon and click
        random_move(x + (w / 2), y + (h / 2), 1)
        # time.sleep(0.9)
        # random_move(x + (w / 2), y + (h / 2), 1, to_up=-15)
        pyautogui.click()
        # add delay to make sure game is loaded properly
        # login()
        automate_gameplay()

    # track the scheduler started in timestamp format
    scheduler = int(time.time()) + (60 * go_work_all_scheduler)

    # set every 3 minutes, do click a round-robin alt-tab with click to avoid server disconnection
    while True:
        print("Run next scheduler at ".format(round_robin_scheduler))
        round_robin_clicker()
        print("Waiting for {} minutes to run next scheduler.".format(round_robin_scheduler))
        time.sleep(round_robin_scheduler * 60)
        # for i in tqdm(range(round_robin_scheduler*60)):
        #     time.sleep(1)


if __name__ == '__main__':
    main()
