import os
import csv
import time
import urllib.parse
from selenium import webdriver
from selenium.webdriver.common.by import By

# Loads previously seen or applied job links
def load_seen_links(file_paths):
    seen_links = set() 
    
    for filepath in file_paths:
        if os.path.exists(filepath):
            with open(filepath, mode='r', encoding='utf-8-sig') as file:
                reader = csv.reader(file, delimiter=';')
                for row in reader:
                    if len(row) >= 3: 
                        link = row[-1].strip()
                        # Ignore header rows
                        if "linkedin.com" in link:
                            seen_links.add(link)
                        
    return seen_links

# Configures and returns the headless browser
def setup_webdriver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('window-size=1920x1080')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    return webdriver.Chrome(options=options)

# Scrapes jobs and filters out seen links
def extract_new_jobs(driver, seen_links, target_count=20):
    new_jobs = []
    scroll_attempts = 0
    max_scrolls = 20
    
    while len(new_jobs) < target_count and scroll_attempts < max_scrolls:
        job_cards = driver.find_elements(By.CSS_SELECTOR, "div.base-card")
        
        for card in job_cards:
            if len(new_jobs) >= target_count:
                break
                
            try:
                link_elem = card.find_element(By.CSS_SELECTOR, "a.base-card__full-link")
                raw_link = link_elem.get_attribute("href")
                # Remove tracking parameters
                clean_link = raw_link.split('?')[0] if '?' in raw_link else raw_link
                
                if clean_link in seen_links:
                    continue
                
                current_session_links = [job[2] for job in new_jobs]
                if clean_link in current_session_links:
                    continue
                    
                title = card.find_element(By.CSS_SELECTOR, "h3.base-search-card__title").text.strip()
                company = card.find_element(By.CSS_SELECTOR, "h4.base-search-card__subtitle").text.strip()
                
                new_jobs.append((title, company, clean_link))
                seen_links.add(clean_link) # Mark as seen immediately
                
            except:
                continue
        
        # Scroll down if more jobs are needed
        if len(new_jobs) < target_count:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            scroll_attempts += 1
            
    return new_jobs

# Appends only new jobs to the CSV file
def save_new_jobs(new_jobs, filepath):
    if not new_jobs:
        print("No new jobs to save.")
        return
        
    file_exists = os.path.isfile(filepath)
    
    with open(filepath, mode='a', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file, delimiter=';')
        
        # Write headers if the file is being created for the first time
        if not file_exists:
            writer.writerow(["Job Title", "Company", "Link"])
            
        writer.writerows(new_jobs)

# Orchestrates all modules
def main(job_title, location, target_count=20):
    print(f"Checking for {target_count} completely new '{job_title}' jobs in '{location}'...")
    
    findings_file = "findings.csv"
    applied_file = "applied.csv"
    
    # Step 1: Load memory
    seen_links = load_seen_links([findings_file, applied_file])
    
    # Step 2: Initialize browser and navigate
    driver = setup_webdriver()
    try:
        title_encoded = urllib.parse.quote(job_title)
        loc_encoded = urllib.parse.quote(location)
        url = f"https://www.linkedin.com/jobs/search?keywords={title_encoded}&location={loc_encoded}&f_TPR=r2592000"
        
        driver.get(url)
        time.sleep(4) # Wait for initial load
        
        # Step 3: Extract
        new_jobs = extract_new_jobs(driver, seen_links, target_count)
        
        # Step 4: Save
        save_new_jobs(new_jobs, findings_file)
        
        print(f"Process complete. Appended {len(new_jobs)} new jobs to '{findings_file}'.")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    main("Computer Engineer", "London", target_count=20)