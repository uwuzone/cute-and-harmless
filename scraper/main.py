# TODO: stop when we see duplicate data
# TODO: fetch followers (may need authentication for this)
# TODO: fetch likes (may need authentication for this)
# TODO: should new user in the replies get added as target?
# TODO(optional): swap sqlite for postgres, will make it easier to distribute jobs
# TODO(optional): better way to handle job state
from typing import List

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from models.base import Base, ScrapeBase
from models.target import Target, JobStatus, new_job_id

from scrapers import exceptions
from scrapers.abstract import Scraper
from scrapers.unauthenticated import UnauthenticatedScraper

engine = create_engine('sqlite:///test.db')

Base.metadata.create_all(engine)
ScrapeBase.metadata.create_all(engine)


class Statement:
    @staticmethod
    def add_targets_statement(targets: List[Target]):
        '''
        Insert targets, ignore duplicates
        '''
        return sqlite_insert(Target).values([
            dict(
                id=target.id,
                username=target.username,
                own_depth=target.own_depth,
                max_depth=target.max_depth,
                max_tweets=target.max_tweets
            )
            for target in targets
        ]).on_conflict_do_nothing(index_elements=[Target.id, Target.username])


def scrape(scraper: Scraper, session: Session, target: Target):
    '''
    Scrape the target.

    High level:
    - Fetch account profile
    - Fetch followers and add them as targets
    - Fetch tweets
      - if any tweet is reply, add the people it replies to as targets
    '''

    def start():
        target.status = JobStatus.RUNNING
        session.merge(target)

    def finish():
        target.status = JobStatus.FINISHED
        session.merge(target)
        session.commit()

    def error():
        target.status = JobStatus.ERROR
        session.merge(target)
        session.commit()

    try:
        start()

        # save account info
        session.merge(scraper.get_user_info())

        # save accounts followed by target as new targets
        for username in scraper.get_following():
            # TODO START HERE: the "following" model expects
            # user IDs but this is usernames. it might be best to simply
            # denormalize usernames and fill them in as the targets get scraped?
            # idk other option is to use usernames as primary key. again, idk
            if target.own_depth < target.max_depth:
                session.execute(
                    Statement.add_targets_statement(
                        target.create_child(username)
                    )
                )

        # save tweets
        for tweet in scraper.get_tweets(max_tweets=target.max_tweets):
            session.merge(tweet)

    except exceptions.UserNotFound as e:
        print(f'SKIPPING {e.username} (user not found)')
        finish()
    except exceptions.UserProtected as e:
        print(f'SKIPPING {e.username} (user is protected)')
        finish()
    except exceptions.UnknownException as e:
        print(f'ERROR (tweety error) {e.username}, {e.info}')
        error()
    except KeyboardInterrupt:
        print(f'ERROR (keyboard interrupt) {target.username}')
        error()
        raise
    except Exception as e:
        print(f'ERROR (unknown error) {target.username}, {e}')
        error()
    else:
        finish()


if __name__ == '__main__':
    with Session(engine) as session:
        username = 'elonmusk'
        root = Target(
            id=new_job_id(username),
            username=username,
            # implies he is the root; this is default
            own_depth=0,
            # max number of additional targets to add on when scraping
            max_branch=None,
            max_depth=4,
            # this is more of a suggestion. we fetch up to the closest number of
            # pages that we expect to return this limit, so you may get slightly
            # more or less than this
            max_tweets=600,
        )
        session.add(root)
        session.commit()

        print(f'JOB: {root.id} starting...')

        while True:
            # find next unclaimed target
            target = session.scalars(
                select(Target).where(
                    Target.id == root.id,
                    Target.status == JobStatus.NEW,
                ).order_by(
                    Target.own_depth
                ).limit(1)
            ).first()
            if (target is None):
                break
            print(
                f'JOB: {target.id} | TARGET: {target.username} | DEPTH {target.own_depth}')
            scraper = UnauthenticatedScraper(target.username)
            scrape(scraper, session, target)
            session.commit()
