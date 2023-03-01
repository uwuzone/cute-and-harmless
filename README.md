# Getting started

Set this environment variables (try https://direnv.net/)

```bash
# default connection for dev
export SCRAPER_PG_USER=postgres
export SCRAPER_PG_PASSWORD=dev
export SCRAPER_PG_HOST=localhost
export SCRAPER_PG_DATABASE=postgres
export SCRAPER_PG_PORT=5432
```

```bash
# start postgres
; docker-compose up --build
; cd scraper
; pipenv install
; pipenv run python admin.py start
; pipenv run python admin.py submit-jobs [usernames go here]
```

# Deploying

- Deploy runner in lambda for unauthenticated jobs
- Deploy runner on something with stable IP for authenticated jobs
