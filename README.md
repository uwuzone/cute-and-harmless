# Getting started

Set this environment variables (try https://direnv.net/)

```bash
# default connection for dev
export CUTE_PG_USER=postgres
export CUTE_PG_PASSWORD=dev
export CUTE_PG_HOST=localhost
export CUTE_PG_DATABASE=postgres
export CUTE_PG_PORT=5432
```

```bash
# start postgres
; docker-compose up -d
; cd scraper
; pipenv install
; pipenv run python admin.py start
; pipenv run python admin.py submit-jobs [usernames go here]
```

# Deploying

- Deploy runner in lambda for unauthenticated jobs
- Deploy runner on something with stable IP for authenticated jobs

# TODO

- sync jobs (particularly important for following/followers)

  - the chrome job is unreliable (usually due to network issues) and sometimes
    stops before getting all data. we should run periodic sync/remedial jobs
    which sweep through the targets list (especially ones close to root
    targets?) and re-scrape their following where we see discrepancies in the
    follower data

- add worker config to the target table (esp user profile, data dir) (maybe
  best to do this with a new worker table) so that it's easier to distribute

- docker version? may not be necessary, only needed if you want mass scraping
  so it depends on usage profile
