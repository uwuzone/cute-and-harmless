import argparse

from sqlalchemy.orm import Session

from models import get_db_engine
from models.target import Worker
from models.target import Target
from models.target import insert_targets_on_conflict_ignore, new_job_id


def add_worker(twitter_username: str, twitter_password: str):
    engine = get_db_engine()
    with Session(engine) as session:
        session.add(
            Worker(
                twitter_username=twitter_username,
                twitter_password=twitter_password,
            )
        )
        session.commit()


def submit_job(username: str, max_followers: int, max_depth: int, max_tweets: int):
    engine = get_db_engine()
    with Session(engine) as session:
        target = Target(
            id=new_job_id(username),
            username=username,
            max_depth=max_depth,
            max_tweets=max_tweets,
            max_followers=max_followers,
            own_depth=0,
        )
        session.execute(insert_targets_on_conflict_ignore([target]))
        session.commit()


def main():
    parser = argparse.ArgumentParser('scraper admin CLI')
    subparsers = parser.add_subparsers(dest='command')

    add_worker_parser = subparsers.add_parser(
        'add-worker', help='Add a scraper worker')
    add_worker_parser.add_argument(
        'username', help='Twitter username for scraper')
    add_worker_parser.add_argument(
        'password', help='Twitter password for scraper')

    submit_job_parser = subparsers.add_parser(
        'submit-job', help='Add a scraping target')
    submit_job_parser .add_argument(
        'username', help='Twitter username for scraper')
    submit_job_parser .add_argument(
        '--max-depth', type=int, help='Max crawl depth', default=4)
    submit_job_parser .add_argument(
        '--max-tweets', type=int, help='Max tweets per account', default=600)
    submit_job_parser .add_argument(
        '--max-followers', type=int, help='Max followers per account', default=200)

    args = parser.parse_args()

    if args.command == 'add-worker':
        add_worker(args.username, args.password)
    if args.command == 'submit-job':
        submit_job(
            args.username,
            max_followers=args.max_followers,
            max_tweets=args.max_tweets,
            max_depth=args.max_depth
        )
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
