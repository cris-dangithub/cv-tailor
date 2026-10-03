# Alex Rivera — knowledge pool (FICTIONAL CANDIDATE, for tests and demos)

Everything in this folder is invented. It shows what a knowledge pool can look like.

## Contact
- Location: Valencia, Spain (open to remote, EU time zones)
- Email: alex.rivera@example.com
- Phone: +34 600 000 000
- Portfolio: https://example.com/alex
- GitHub: https://github.com/example-alex (fictional)
- Languages: Spanish (native), English (C1, IELTS 7.5 in 2022)

## Work history

### Northwind Logistics — Data Engineer (March 2023 – present, hybrid, Valencia)
- Moved the nightly warehouse load from cron scripts to Airflow 2 with retries and SLAs; failed
  loads went from about 6 a month to 1 a quarter (measured in the incident log).
- Built the dbt project for the finance marts (42 models), with tests that block the merge in
  GitHub Actions.
- Designed the CDC pipeline from PostgreSQL to BigQuery with Debezium and Pub/Sub; reports that
  were a day old now refresh every 15 minutes.
- On call one week in five for the data platform; wrote the runbooks for the five most common
  failures.
- Mentored one junior analyst through their first dbt models (6 months).

### Tidewater Retail — Data Analyst (June 2020 – February 2023, Madrid)
- Replaced a weekly Excel sales report with a Looker dashboard used by 40 store managers.
- Wrote the SQL behind the stock-out alert that the supply team still uses.
- Automated the monthly supplier scorecard in Python (pandas): from two days of manual work to
  one hour.

## Projects
- **tide-forecast** (personal, 2024): a demand-forecasting notebook with Prophet on public retail
  data; not deployed.
- **open-gtfs-loader** (open source contribution, 2023): fixed the timezone handling of the GTFS
  loader; 2 merged pull requests.

## Education
- MSc Data Science, Universitat Politècnica de València (2019 – 2020)
- BSc Statistics, Universidad Complutense de Madrid (2015 – 2019)
- Certificate: Google Cloud Professional Data Engineer (2024) — https://example.com/cert/gcp-pde

## Skills (as the candidate states them)
- Production: SQL, Python, dbt, Airflow, BigQuery, PostgreSQL, GitHub Actions, Looker
- Some experience: Debezium, Pub/Sub, Terraform (read and small changes only)
- Learning: Spark (course only, no production use)
