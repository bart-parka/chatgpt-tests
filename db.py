from tinydb import TinyDB, Query
db = TinyDB('db.json')


def store_elongated_tweet(tweet):
    db.insert(tweet)


def retrieve_cached_tweets():
    return db.all()


def tweet_dupe_check(tweet_id):
    store = True
    if len(db.all()) > 0:
        for each in db.all():
            if each["id"] == tweet_id:
                store = False
        return store
    else:
        return True