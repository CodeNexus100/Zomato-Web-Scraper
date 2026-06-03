import re
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

def get_restaurant_name(driver, wait):
    try:
        name_el = wait.until(EC.visibility_of_element_located((By.XPATH, "//h1")))
        return name_el.text.strip()
    except:
        return None


def get_ratings(driver, wait):
    ratings = {}
    # Dining
    try:
        din_score_el = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[text()='Dining Ratings']/preceding::div[contains(@class,'cILgox')][1]")
            )
        )
        din_score = float(din_score_el.text.strip())
        din_count_el = din_score_el.find_element(By.XPATH, "following::div[contains(@class,'kEgyiI')][1]")
        din_count = int(din_count_el.text.strip().replace(",", ""))
        ratings["dining"] = {"score": din_score, "count": din_count}
    except:
        pass

    # Delivery
    try:
        del_score_el = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[text()='Delivery Ratings']/preceding::div[contains(@class,'cILgox')][1]")
            )
        )
        del_score = float(del_score_el.text.strip())
        del_count_el = del_score_el.find_element(By.XPATH, "following::div[contains(@class,'kEgyiI')][1]")
        del_count = int(del_count_el.text.strip().replace(",", ""))
        ratings["delivery"] = {"score": del_score, "count": del_count}
    except:
        pass

    return ratings


def get_cuisines(driver, wait):
    try:
        cuisine_els = wait.until(EC.presence_of_all_elements_located(
            (By.XPATH, "//section//div[contains(@class,'fXdtVd')]//a")
        ))
        cuisines = []
        for c in cuisine_els:
            text = c.text.strip()
            if text and text not in cuisines:
                cuisines.append(text)
        return cuisines
    except:
        return []


def get_address(driver):
    try:
        addr_el = driver.find_element(By.XPATH, "//section//div[contains(@class,'ckqoPM')]")
        return addr_el.text.strip()
    except:
        return None


def get_timing(driver):
    try:
        timing_el = driver.find_element(
            By.XPATH, "//section//span[contains(text(),'am') or contains(text(),'pm') or contains(text(),'–')]"
        )
        return timing_el.text.strip()
    except:
        return None


def get_cost_for_two(driver):
    try:
        cost_el = driver.find_element(
            By.XPATH, "//section//div[contains(@class,'ePRRqr') and contains(text(),'₹')]"
        )
        return cost_el.text.strip()
    except:
        return None


def get_phone(driver):
    try:
        phone_el = driver.find_element(
            By.XPATH, "//a[starts-with(@href,'tel:') and contains(@class,'leEVAg')]"
        )
        return phone_el.text.strip()
    except:
        return None

# Scraping specific restaurant by its link
def scrap_full_restaurant(driver, link, wait_time=25):
    wait = WebDriverWait(driver, wait_time)

    def safe_click(xpath):
        try:
            btn = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
            btn.click()
            time.sleep(2)
            return True
        except Exception:
            return False

    def load_all_scroll():
        pause = 1.2
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(pause)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def get_all_images(selector):
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
        urls = []
        for el in elements:
            try:
                src = (el.get_attribute("src") or
                       el.get_attribute("data-src") or
                       el.get_attribute("srcset"))
                if src:
                    urls.append(src)
            except:
                pass
        return list(set(urls))

    def clean_filename(name):
        return re.sub(r'[^a-zA-Z0-9_-]+', '_', name.strip())

    driver.get(link)
    time.sleep(3)
    title = driver.title.split('|')[0].strip()
    safe_title = clean_filename(title)

    dishes = []
    if safe_click("//*[text()='Order Online']"):
        time.sleep(3)
        cards = driver.find_elements(By.XPATH, "//*[contains(@class,'sc-iLWYPX')]")
        for card in cards:
            try:
                dish = {
                    "name": card.find_element(By.TAG_NAME, "h4").text,
                    "price": card.find_element(By.TAG_NAME, "span").text,
                    "detail": card.find_element(By.CLASS_NAME, "sc-isojaI").text
                }
                dishes.append(dish)
            except:
                pass

    photos = []
    if safe_click("//*[text()='Photos']"):
        load_all_scroll()
        photos = get_all_images("img.sc-s1isp7-5")

    menu_photos = []
    if safe_click("//*[text()='Menu']"):
        load_all_scroll()
        menu_photos = get_all_images("img.sc-s1isp7-5")

    data = {
        "restaurant_name": title,
        "url": link,
        "dishes": dishes,
        "photos": photos,
        "menu_photos": menu_photos
    }

    return data

