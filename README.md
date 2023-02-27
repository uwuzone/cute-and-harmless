# silly little twitter cralwer

- **target** - a user to scrape
- **job** - the task of scraping a graph of users connected to some root target
  - all targets acquired by crawling from a given root target will have the same job ID by default

# Getting started

Set this environment variables (try https://direnv.net/)

```bash
# login info for scraper account.
# do not use your main account! you will get banned
export CUTE_SCRAPER_USERNAME=
export CUTE_SCRAPER_PASSWORD=

# chrome profile info. if provided, your chrome session will get saved here so
# you don't have to log in over and over (which is a really the quick way to get
# flagged as sus)
#
# The directories don't have to exist---they'll get created the first time you
# run the scraper
export CUTE_SCRAPER_USER_DATA_DIR=/tmp/userdata-example
export CUTE_SCRAPER_PROFILE_DIR=/tmp/profile-example

# target/job info. You must provide at least one of these. If both are provided,
# "resume_job_id" takes precedence.
#
# root target is a username
export CUTE_SCRAPER_ROOT_TARGET=
# or resume a job you'll see the job id when scraping starts (you can also query db)
export CUTE_SCRAPER_RESUME_JOB_ID=

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
; pipenv run python main.py
```

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
