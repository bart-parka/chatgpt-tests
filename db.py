from tinydb import TinyDB, Query
db = TinyDB('db.json')


def store_elongated_tweet(tweet):
    db.insert(tweet)


def retrieve_cached_tweets():
    return db.all()