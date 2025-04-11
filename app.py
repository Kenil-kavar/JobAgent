import streamlit as st
import time
import os
from bs4 import BeautifulSoup
import yagmail
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
load_dotenv()
# ------------------ Configuration ------------------
LINKEDIN_URL = "https://www.linkedin.com/jobs/search/?keywords=ML%20intern&f_TPR=r604800&geoId=101588871&origin=JOB_SEARCH_PAGE_SEARCH_BUTTON&refresh=true"
SENT_JOBS_FILE = "sent_jobs.txt"
FIRST_RUN_FLAG = "first_run.txt"

SENDER_EMAIL = os.getenv("SENDER")
APP_PASSWORD = os.getenv("PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER")

# ------------------ LangGraph State Schema ------------------
class JobState(TypedDict):
    new_jobs: List[Dict[str, str]]

# ------------------ Scrape LinkedIn Jobs ------------------
def scrape_linkedin_jobs(_: JobState) -> JobState:
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0")

    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.get(LINKEDIN_URL)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "job-card-container__link"))
        )

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(5)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        driver.quit()

        job_links = soup.find_all('a', class_='job-card-container__link job-card-list__title--link')
        jobs = []
        for link_elem in job_links:
            href = link_elem.get('href')
            title = link_elem.get_text(strip=True)
            if href and title and '/jobs/view/' in href:
                clean_href = href.split('?')[0]
                full_url = f"https://www.linkedin.com{clean_href}"
                jobs.append({
                    "title": title,
                    "link": full_url
                })

        unique_jobs = [dict(t) for t in {tuple(sorted(d.items())) for d in jobs}]
        is_first_run = not os.path.exists(FIRST_RUN_FLAG)

        try:
            with open(SENT_JOBS_FILE, "r") as f:
                sent_links = set(f.read().splitlines())
        except FileNotFoundError:
            sent_links = set()

        if is_first_run:
            with open(SENT_JOBS_FILE, "w") as f:
                for job in unique_jobs:
                    f.write(f"{job['link']}\n")
            with open(FIRST_RUN_FLAG, "w") as f:
                f.write("completed")
            return {"new_jobs": []}
        else:
            new_jobs = [job for job in unique_jobs if job["link"] not in sent_links]
            if new_jobs:
                with open(SENT_JOBS_FILE, "a") as f:
                    for job in new_jobs:
                        f.write(f"{job['link']}\n")
            return {"new_jobs": new_jobs}

    except Exception as e:
        st.error(f"Scraping error: {e}")
        return {"new_jobs": []}

# ------------------ Send Email ------------------
def send_email_notification(state: JobState) -> JobState:
    new_jobs = state["new_jobs"]
    if not new_jobs:
        st.info("No new jobs found.")
        return state

    yag = yagmail.SMTP(SENDER_EMAIL, APP_PASSWORD)
    body = "\n\n".join([f"{job['title']}\n{job['link']}" for job in new_jobs])
    subject = f"[ML Intern Jobs] {len(new_jobs)} new posting(s) found!"

    try:
        yag.send(to=RECEIVER_EMAIL, subject=subject, contents=body)
        st.success("📧 Email sent with new job postings!")
    except Exception as e:
        st.error(f"Email error: {e}")

    return state

# ------------------ LangGraph Setup ------------------
builder = StateGraph(JobState)
builder.add_node("scrape_jobs", scrape_linkedin_jobs)
builder.add_node("send_email", send_email_notification)
builder.set_entry_point("scrape_jobs")
builder.add_edge("scrape_jobs", "send_email")
builder.add_edge("send_email", END)
graph = builder.compile()

# ------------------ Streamlit App ------------------
st.title("🔍 LinkedIn ML Intern Job Scraper")

if st.button("🚀 Start Scraping"):
  while True
    with st.spinner("Scraping jobs and sending emails..."):
        graph.invoke({"new_jobs": []})
        time.sleep(5)
