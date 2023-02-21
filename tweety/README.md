# Unauthenticated tweet scraper/crawler

Given a user (called the root user or crawl root), this bot will scrape the
user's tweets and replies. When the bot encounters a tweet mentioning/replying
to another user, the new user is added to a queue for further scraping, up to
a configurable recursion depth.

# Getting started

```bash
$ pipenv install
$ pipenv run python main.py
```
