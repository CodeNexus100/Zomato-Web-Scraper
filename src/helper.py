import time
from selenium.webdriver.common.by import By
# Helper functions

def safe_text(parent, xpath):
    try:
        return parent.find_element(By.XPATH, xpath).text.strip()
    except:
        return ""

def get_image_and_link(card):
    """Extract image URL and restaurant page link from a card"""
    image_url = ""
    link_url = ""
    
    # Try to get the <a> link
    try:
        a_tag = card.find_element(By.XPATH, ".//a[contains(@class,'sc-hqGPoI')]")
        link_url = a_tag.get_attribute("href")
    except:
        pass

    # Try to get the <img> element inside card
    try:
        img = card.find_element(By.XPATH, ".//img")
        possible_attrs = ["src", "data-src", "data-original", "data-srcset", "srcset"]

        for attr in possible_attrs:
            val = img.get_attribute(attr)
            if val and "http" in val:
                if " " in val:
                    val = val.split(" ")[0]  # handle srcset
                image_url = val
                break
    except:
        pass

    return image_url, link_url

def scroll_full_page(driver, pause_time=1.5):
    """Scrolls to bottom of page to load all restaurants"""
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause_time)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def get_links(element):
    links = []

    if element.tag_name.lower() == "a":
        href = element.get_attribute("href")
        if href:
            links.append(href)

    nested_links = element.find_elements(By.XPATH, ".//a[@href]")
    for link in nested_links:
        links.append(link.get_attribute("href"))

    return list(set(links))   # remove duplicates