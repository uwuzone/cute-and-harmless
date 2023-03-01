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
; docker-compose up

# in another terminal
; cd scraper
; pipenv install
; pipenv run python admin.py start
; pipenv run python admin.py submit-jobs [usernames go here]
```

# Deploying

- Deploy runner in lambda for unauthenticated jobs
- Deploy runner on something with stable IP for authenticated jobs

# Lambda

```
just build-lambda
```

NB: the official amazon linux image for python 3.9 has like, years-old hardcoded
amazon forks of official yum repos baked in so you can't get up-to-date
libraries in some cases (notable libpq), so this uses a custom image. Instead of
building in the lambda emulator, you should do this for testing lambda locally:

1. Follow steps to download the emulator for your architecture [here](https://github.com/aws/aws-lambda-runtime-interface-emulator#test-an-image-without-adding-rie-to-the-image)
2. Start postgres `docker-compose up -d`
3. Find the docker compose network with `docker network`
4. Start the lambda container with the emulator mounted like this

```bash
docker run \
    --rm -it \
    --network <YOUR COMPOSE NETWORK HERE> \
    # you must be in the correct compose network or this
    # db host will not resolve!
    -e SCRAPER_PG_HOST=db \
    -e SCRAPER_PG_USER=postgres \
    -e SCRAPER_PG_PASSWORD=dev \
    -e SCRAPER_PG_DATABASE=postgres \
    -e SCRAPER_PG_PORT=5432 \
    # path to your emulator download goes before the colon
    -v ~/.aws-lambda-rie:/aws-lambda \
    -p 9000:8080 \
    # entrypoint changed to the emulator
    --entrypoint /aws-lambda/aws-lambda-rie \
    twitterscraper:lambda \
    /usr/local/bin/python -m awslambdaric lambda.handler
```
