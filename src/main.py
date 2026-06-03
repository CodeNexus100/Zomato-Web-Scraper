
import time
import json
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from datetime import datetime
from queue import Queue
import concurrent.futures

from helper import ( 
    get_links, safe_text, scroll_full_page
)
from scraping_restaurant import (
    get_address, get_cost_for_two, get_cuisines, 
    get_phone, get_ratings, get_restaurant_name, 
    get_timing, scrap_full_restaurant
)

# Get city input from user
city_input = input("Enter the city name (e.g., mumbai, pune, bangalore): ").strip().lower().replace(" ", "-")

# Basic driver setup

driver = webdriver.Chrome()
driver.maximize_window()
wait = WebDriverWait(driver, 25)

print(f"Opening Zomato for {city_input}…")
driver.get(f"https://www.zomato.com/{city_input}/restaurants")

# handling cookie popup

try:
    btn = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//*[contains(text(),'Accept')]")
    ))
    btn.click()
    print("Cookies accepted.")
except:
    print("No cookie popup.")

# scroll down

driver.execute_script("window.scrollTo(0, 500);")
time.sleep(1.5)

# Scrolling full page

print("Scrolling full page…")
scroll_full_page(driver)

# find all cards of restaurants 

cards = driver.find_elements(
    By.XPATH, "//a[contains(@class,'sc-hPeUyl') and contains(@class,'cKQNlu')]"
)

print(f"Found {len(cards)} restaurant cards.")

# Get basic informaion from home restaurant page of all restaurants

restaurants = []

for idx, card in enumerate(cards, start=1):

    driver.execute_script("arguments[0].scrollIntoView(true);", card)
    time.sleep(0.1)

    name = safe_text(card, ".//h4")
    cuisine = safe_text(card, ".//p[contains(@class,'fSxdnq')]")
    price = safe_text(card, ".//p[contains(@class,'KXcjT')]")
    location = safe_text(card, ".//div[contains(@class,'min-basic-info-left')]/p")
    page_link = get_links(card)

    restaurants.append({
        "name": name,
        "cuisine": cuisine,
        "price_for_two": price,
        "location": location,
        # "image_url": img_url,
        "page_link": page_link
    })

    if idx % 25 == 0:
        print(f"{idx} restaurants processed…")

print("Extraction completed.")

# saving this basic restaurants information 

# timestamp generate
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

filename = f"final_restaurants_info_{timestamp}.json"

with open(filename, "w", encoding="utf-8") as f:
    json.dump(restaurants, f, ensure_ascii=False, indent=4)

print(f"Exported JSON with {len(restaurants)} restaurants to {filename}")

# Checking the restaurants links from list of all restaurants

# count = 0
# for rest in restaurants:
#     if count > 3:
#         break
#     print('-------------------------')
#     print(rest['page_link'][0])
#     print('-------------------------')
#     count += 1

# Closing the first driver
driver.quit()

# Scrap each restaurant by its link

def scrap_restaurant_full(driver, rest_id, url, timeout=15):
    wait = WebDriverWait(driver, timeout)
    restaurant = {
        "id": rest_id,
        "name": None,
        "ratings": {},
        "cuisines": [],
        "address": None,
        "timing": None,
        "cost_for_two": None,
        "phone": None
    }

    driver.get(url)
    time.sleep(2)

    restaurant["name"] = get_restaurant_name(driver, wait)
    if restaurant["name"]:
        print('name is added successfully')
    else:
        print(f'something problem')
        
    restaurant["ratings"] = get_ratings(driver, wait)
    if restaurant["ratings"]:
        print('ratings is added successfully')
    else:
        print(f'something problem')
        
    restaurant["cuisines"] = get_cuisines(driver, wait)
    if restaurant["cuisines"]:
        print('cuisines is added successfully')
    else:
        print(f'something problem')
        
    restaurant["address"] = get_address(driver)
    if restaurant["address"]:
        print('address is added successfully')
    else:
        print(f'something problem')
    
    restaurant["timing"] = get_timing(driver)
    if restaurant["timing"]:
        print('timing is added successfully')
    else:
        print(f'something problem')
        
    restaurant["cost_for_two"] = get_cost_for_two(driver)
    if restaurant["cost_for_two"]:
        print('cost_for_two is added successfully')
    else:
        print(f'something problem')
    
    restaurant["phone"] = get_phone(driver)
    if restaurant["phone"]:
        print('restaurant["phone"] is added successfully')
    else:
        print(f'something problem')
        
    restaurant_details = scrap_full_restaurant(driver, url)
    if restaurant_details:
        print('restaurant_details is added successfully')
    else:
        print('something problem')
    
    restaurant["dishes"] = restaurant_details.get("dishes", [])
    restaurant["photos"] = restaurant_details.get("photos", [])
    restaurant["menu_images"] = restaurant_details.get("menu_photos", [])

    return restaurant

# # loop thorugh the restaurant

# Function to split list into chunks
def chunk_list(lst, chunk_size):
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]

chunk_size = 100
chunks = list(chunk_list(restaurants, chunk_size))

total_restaurants = len(restaurants)
scraped_count = 0

num_threads = 5
driver_queue = Queue()
print(f"Initializing {num_threads} webdrivers for faster scraping...")
for _ in range(num_threads):
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-gpu')
    # Adding a strategy to load page faster
    options.page_load_strategy = 'eager'
    d = webdriver.Chrome(options=options)
    driver_queue.put(d)

def scrape_task(task_data):
    idx, r = task_data
    print(f"Scraping restaurant {idx} of {total_restaurants}: {r['name']}")
    driver = driver_queue.get()
    try:
        data = scrap_restaurant_full(driver, idx, r["page_link"][0])
        return data
    except Exception as e:
        print(f"Error scraping {r['name']}: {e}")
        return None
    finally:
        driver_queue.put(driver)

for part_idx, chunk in enumerate(chunks, 1):
    start_idx = scraped_count + 1
    end_idx = scraped_count + len(chunk)
    
    # Generate timestamp for filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"scraped_restaurants_from_{start_idx}_to_{end_idx}_{timestamp}.json"
    
    print(f"\nScraping part {part_idx} ({start_idx} to {end_idx}) ...")
    
    part_results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        results = list(executor.map(scrape_task, enumerate(chunk, start_idx)))
        
    for data in results:
        if data:
            part_results.append(data)
    
    # Save this chunk immediately
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(part_results, f, ensure_ascii=False, indent=2)
    
    print(f"Saved {len(part_results)} records to {output_file}")
    
    scraped_count += len(chunk)
    
    # Optional pause
    time.sleep(5)

# Close all drivers
while not driver_queue.empty():
    d = driver_queue.get()
    d.quit()

print("Scraping complete!")

