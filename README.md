## Scraping individual athlete trials from Tilastopaja 

This script scrapes individual athlete trial data from the online athletics database Tilastopaja (https://www.tilastopaja.info). It:

1. Grabs the top 100 athletes in the world for a specific event and sex (from Tilastopaja leaderboard page), for the specified leaderboard years
2. Collects a unique list of top athletes across these years
3. For each of these athletes, the script:
    - opens their individual results page (each year has a separate page)
    - extracts each trial from their competition results table
    - does this for each specified year
4. All scraped data is combined and appended to a single data frame with one row = one trial result

The final data frame contains columns:
- year
- athlete
- location
- date
- result 

With event and sex in the filename. 

Additional cleaning may be required to filter out instances where athletes compete in multiple events (e.g. triple jump results may show up in a long jump scrape if an athlete has competed in both). 

### Command line arguments
The script requires the following arguments:
--event
--sex
--username
--password
--leaderboard-start-year
--leaderboard-end-year
--data-start-year
--data-end-year

- Event codes for multi-trial events are given in the file tila_event_codes.csv. 
- Sex code (1 = men, 2 = women)
- A valid Tilastopaja subscription and login are required. 

### Example usage
python main.py \
  --event 330 \
  --sex 1 \
  --username your_username \
  --password your_password \
  --leaderboard-start-year 2022 \
  --leaderboard-end-year 2025 \
  --data-start-year 2020 \
  --data-end-year 2025

This would identify the unique athletes ranked in the top 100 for men's long jump from 2022-2025, and scrape their individual trial data from 2020-2025. 

