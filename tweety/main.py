# TODO: stop when we see duplicate data
# TODO: fetch followers (may need authentication for this)
# TODO: fetch likes (may need authentication for this)
# TODO(optional): swap sqlite for postgres, will make it easier to distribute jobs
from typing import List, Optional

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from tweety import exceptions_ as tw_exceptions
from tweety.bot import Twitter

from models.base import Base, ScrapeBase
from models.account import Account
from models.target import Target, JobStatus, new_job_id
from models.interaction import Tweet

DEFAULT_MAX_TWEETS = 200

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
                handle=target.handle,
                own_depth=target.own_depth,
                max_depth=target.max_depth,
                max_tweets=target.max_tweets
            )
            for target in targets
        ]).on_conflict_do_nothing(index_elements=[Target.id, Target.handle])


def get_follows(handle: str) -> List[str]:
    '''Get list of follows as usernames.'''
    # TODO
    return []


def get_target_follows_as_targets(target: Target) -> List[Target]:
    '''Return a new child target for each of the target's follows.'''
    return [
        target.create_child(handle)
        for handle in get_follows(target.handle)
    ]


def scrape_target(session: Session, target: Target):
    '''
    Scrape the target.

    High level:
    - Fetch account profile
    - Fetch followers and add them as targets
    - Fetch tweets
      - if any tweet is reply, add the people it replies to as targets
    '''

    # XXX: not a good idea to do the status updates this way tbh, should do
    # something more like `update target set status = 'running' returning ...`

    def start():
        target.status = JobStatus.RUNNING
        session.merge(target)

    def finish(cursor: str | None):
        target.status = JobStatus.FINISHED
        target.tweety_last_cursor = cursor
        session.merge(target)
        session.commit()

    def error(cursor: str | None):
        target.status = JobStatus.ERROR
        target.tweety_last_cursor = cursor
        session.merge(target)
        session.commit()

    latest_cursor: Optional[str] = None
    try:
        start()

        branch = 0
        bot = Twitter(target.handle)
        user_info = bot.get_user_info()

        child_targets = get_target_follows_as_targets(target)
        if len(child_targets):
            session.execute(Statement.add_targets_statement(child_targets))

        # save account info
        account = Account(
            profile_url=user_info.profile_url,
            rest_id=user_info.rest_id,
            display_name=user_info.name,
            handle=user_info.screen_name,
            joined_at=user_info.created_at,
            description=user_info.description,
            location=user_info.location,
            protected=user_info.protected,
            verified=user_info.verified,
            tw_possibly_sensitive=user_info.possibly_sensitive,
            tw_verified_type=user_info.verified_type,
            tw_normal_followers_count=user_info.normal_followers_count,
            tw_statuses_count=user_info.statuses_count,
            tw_media_count=user_info.media_count,
            tw_listed_count=user_info.listed_count,
            tw_fast_followers_count=user_info.fast_followers_count,
            tw_favourites_count=user_info.favourites_count,
            tw_followers_count=user_info.followers_count,
            tw_friends_count=user_info.friends_count,
        )
        session.merge(account)

        # save tweets
        max_tweets = target.max_tweets or DEFAULT_MAX_TWEETS
        pages = max(max_tweets // 20, 1)
        all_tweets = bot.get_tweets(pages=pages, replies=True, wait_time=3)
        for _tweet in all_tweets:
            raw: dict = _tweet._get_original_tweet()
            tweet = Tweet(
                rest_id=_tweet.id,
                created_on=_tweet.created_on,
                content=_tweet.text,
                author_rest_id=_tweet.author.rest_id,
                reply_count=_tweet.reply_counts,  # yes
                like_count=_tweet.likes,
                retweet_count=_tweet.retweet_counts,
                quote_count=_tweet.quote_counts,
                is_retweet=_tweet.is_retweet,
                is_reply=_tweet.is_reply,
                reply_to_account_rest_id=raw.get(
                    'in_reply_to_user_id_str', None),
                reply_to_tweet_rest_id=raw.get(
                    'in_reply_to_status_id_str', None),
                tw_is_possibly_sensitive=_tweet.is_possibly_sensitive,
            )
            session.merge(tweet)

            # every new user in the replies gets added as a target
            if tweet.reply_to_account_rest_id is not None:
                if target.own_depth < target.max_depth:
                    if target.max_branch is None or branch < target.max_branch:
                        branch += 1
                        new_target = target.create_child(
                            raw['in_reply_to_screen_name'])
                        session.execute(
                            Statement.add_targets_statement([new_target]))

        # keep record of how far we scraped in history
        latest_cursor = all_tweets.cursor

    except tw_exceptions.UserNotFound:
        print(f'SKIPPING {target.handle} (user not found)')
        finish(latest_cursor)
    except tw_exceptions.UserProtected:
        print(f'SKIPPING {target.handle} (user is protected)')
        finish(latest_cursor)
    except tw_exceptions.UnknownError as e:
        print(f'ERROR (tweety error) {target.handle}, {e}')
        error(latest_cursor)
    except KeyboardInterrupt:
        print(f'ERROR (keyboard interrupt) {target.handle}')
        error(latest_cursor)
        raise
    except Exception as e:
        print(f'ERROR (unknown error) {target.handle}, {e}')
        error(latest_cursor)
    else:
        finish(latest_cursor)


if __name__ == '__main__':
    with Session(engine) as session:
        handle = 'elonmusk'
        root = Target(
            id=new_job_id(handle),
            handle=handle,
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
                f'JOB: {target.id} | TARGET: {target.handle} | DEPTH {target.own_depth}')
            scrape_target(session, target)
            session.commit()
