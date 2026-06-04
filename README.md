# Zomato Restaurant Data Extractor Backend

A high-performance backend service for collecting restaurant information from Zomato city listings using Playwright and FastAPI.

The application automatically discovers restaurant pages, extracts restaurant metadata, processes results concurrently, and generates structured datasets in JSON and Excel formats.

## Features

* Multi-threaded / concurrent restaurant scraping
* Automatic restaurant discovery by city
* FastAPI-powered backend
* Real-time job progress tracking
* JSON export support
* Excel (.xlsx) export support
* Background scraping jobs
* Live data updates during execution
* Retry and fault-tolerant scraping workflow
* Scalable architecture for deployment

## Data Extracted

For each restaurant, the scraper collects:

* Restaurant Name
* Phone Number
* Address
* Cuisine
* Rating
* Zomato URL

Example:

```json
{
  "restaurant_name": "Hyderabadi Biryani",
  "phone_number": "+919559694583",
  "address": "138/30/1A, MG Marg, Civil Lines, Allahabad",
  "cuisine": "North Indian, Mughlai, Biryani, Chinese, Rolls",
  "rating": "4.1",
  "zomato_url": "https://www.zomato.com/allahabad/hyderabadi-biryani-civil-lines"
}
```

## Tech Stack

### Backend

* FastAPI
* Uvicorn

### Scraping Engine

* Playwright
* Chromium (Headless)

### Data Processing

* Pandas
* OpenPyXL

### Deployment

* Railway / Render Compatible
* Docker Ready

## Project Structure

```bash
backend/
│
├── app/
│   ├── api/
│   ├── scraper/
│   ├── services/
│   ├── models/
│   └── utils/
│
├── jobs/
├── output/
├── logs/
│
├── main.py
├── requirements.txt
└── README.md
```

## Installation

Clone the repository:

```bash
git clone <repository-url>
cd backend
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate the environment:

Windows:

```bash
venv\Scripts\activate
```

Linux/macOS:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Install Playwright browsers:

```bash
playwright install chromium
```

## Running the Backend

Start the FastAPI server:

```bash
uvicorn main:app --reload
```

Server:

```text
http://localhost:8000
```

Swagger Documentation:

```text
http://localhost:8000/docs
```

## API Workflow

### Start a Scraping Job

```http
POST /api/scrape
```

Request:

```json
{
  "city": "allahabad",
  "limit": 100
}
```

Response:

```json
{
  "job_id": "abc123"
}
```

---

### Get Job Progress

```http
GET /api/progress/{job_id}
```

Response:

```json
{
  "status": "running",
  "completed": 43,
  "total": 100
}
```

---

### Fetch Current Results

```http
GET /api/results/{job_id}
```

Returns all collected restaurant records up to the current point in execution.

---

### Download Excel File

```http
GET /api/download/{job_id}
```

Returns the generated Excel file once scraping is complete.

## Concurrency

The scraper utilizes concurrent browser workers to improve extraction speed while maintaining stability.

Benefits:

* Faster execution
* Improved throughput
* Reduced overall scraping time
* Better resource utilization

## Output Formats

### JSON

```json
[
  {
    "restaurant_name": "...",
    "phone_number": "...",
    "address": "...",
    "rating": "...",
    "cuisine": "...",
    "zomato_url": "..."
  }
]
```

### Excel

Generated automatically:

```text
allahabad_restaurants.xlsx
```

## Error Handling

The application includes:

* Automatic retries
* Timeout handling
* Failed page recovery
* Duplicate prevention
* Progress persistence

## Future Improvements

* Proxy rotation support
* Scheduled scraping jobs
* PostgreSQL integration
* User authentication
* Cloud storage support
* Analytics dashboard
* Multi-city scraping

## Disclaimer

This project is intended for educational, research, and data-processing purposes. Users are responsible for ensuring compliance with the terms of service, robots.txt policies, and applicable laws when using this software.

## Author

Kartikey Gupta

Built with FastAPI, Playwright, and Python.
