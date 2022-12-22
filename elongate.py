import requests
import string
import os
import random
import logging
import argparse
import sys
from datetime import datetime, timezone, timedelta
from mdutils.mdutils import MdUtils
from chatgpt_wrapper import ChatGPT

# Parse command line arguments
parser = argparse.ArgumentParser(description="Tweet ElonGator",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-l", "--log", help="Logging Level", default="INFO")
args = parser.parse_args()
config = vars(args)
print("Arguments Passed in: {}".format(config))

# assuming loglevel is bound to the string value obtained from ther
# command line argument. Convert to upper case to allow the user to
# specify --log=DEBUG or --log=debug
numeric_level = getattr(logging, args.log.upper(), None)
if not isinstance(numeric_level, int):
    raise ValueError('Invalid log level: %s' % args.log)
logging.basicConfig(filename='elongate.log', level=numeric_level)


def auth():
    return os.getenv('TOKEN')


def create_headers(bearer_token):
    headers = {"Authorization": "Bearer {}".format(bearer_token)}
    return headers


def create_url(query_string, start_date, end_date, max_results=10):
    search_url = "https://api.twitter.com/2/tweets/search/recent"

    # change params based on the endpoint you are using
    query_params = {
        'query': query_string,
        'start_time': start_date,
        'end_time': end_date,
        'max_results': max_results,
        'expansions': 'author_id,in_reply_to_user_id,geo.place_id',
        'tweet.fields': 'id,text,author_id,in_reply_to_user_id,geo,conversation_id,created_at,lang,public_metrics,referenced_tweets,reply_settings,source',
        'user.fields': 'id,name,username,created_at,description,public_metrics,verified',
        'place.fields': 'full_name,id,country,country_code,geo,name,place_type',
        'next_token': {}}
    return search_url, query_params


def generate_embed_html(user_id, tweet_id):
    tweet_url = "https://twitter.com/{}/status/{}".format(user_id, tweet_id)
    response = requests.request("GET", "https://publish.twitter.com/oembed?url={}".format(tweet_url))
    if response.status_code != 200:
        raise Exception(response.status_code, response.text)
    return response.json()["html"]


def connect_to_endpoint(url, headers, params, next_token=None):
    params['next_token'] = next_token  # params object received from create_url function
    response = requests.request("GET", url, headers=headers, params=params)
    print("Endpoint Response Code: " + str(response.status_code))
    if response.status_code != 200:
        raise Exception(response.status_code, response.text)
    return response.json()


def generate_query_string(users):
    from_strings = []
    for user in users:
        from_string = "from:{}".format(user)
        from_strings.append(from_string)
    query_string = "(" + ' OR '.join(from_strings) + ")" + " -is:retweet -is:reply"
    return query_string


def generate_start_end_times(number_days):
    """
    How many days of recent tweets to look at?
    """

    # Ensure 'days' is a positive integer.
    assert (
        isinstance(number_days, int) and number_days > 0
    ), "Value of 'days' must be a positive integer."

    now = datetime.now() - timedelta(seconds=10)  # End time must be at least 10 seconds in the past
    previous_day = now - timedelta(days=number_days)

    start_time = previous_day.replace(tzinfo=timezone.utc).isoformat()  # convert to RFC3339 date-time
    end_time = now.replace(tzinfo=timezone.utc).isoformat()  # convert to RFC3339 date-time

    return start_time, end_time


def generate_markdown_file(paragraphs):
    now = datetime.now()
    md_file = MdUtils(file_name='ElonGator', title='ElonGator')
    for para in paragraphs:
        md_file.new_paragraph(para)
    md_file.write('  \n')
    md_file.create_md_file()


def elongate_tweet(tweet_text):
    questions = [
        "Can you explain this tweet: ",
        "Can you expand on this tweet: ",
        "Can you give me background on this tweet: ",
        "Can you give some context for this tweet: "
    ]

    # Removing any non-printable characters before feeding to ChatGPT, not sure if required
    printable = set(string.printable)

    question_and_tweet = "{}".format(random.choice(questions)) + ''.join(filter(lambda x: x in printable, tweet_text))

    logging.debug("ChatGPT question and tweet:\n" + question_and_tweet)

    #output = bot.ask(question_and_tweet)
    output = ""
    for iterator in bot.ask_stream(question_and_tweet):
        sys.stdout.write(iterator)
        sys.stdout.flush()
        output = output + iterator

    logging.debug("ChatGPT output:\n" + output)

    return output

if __name__ == '__main__':

    # Make sure you login first using `chatgpt install`
    bot = ChatGPT()

    users_list = [
        # "engineers_feed",  # The first 10 are returned in order I think?
        "BBCBreaking",
        "cnnbrk"
        # "sama",
        # "balajis",
        # "tobi",
    ]

    query = generate_query_string(users_list)
    bearer_token = auth()
    headers = create_headers(bearer_token)
    query_start_time, query_end_time = generate_start_end_times(1)
    url, query_parameters = create_url(query, query_start_time, query_end_time, 10)
    json_response = connect_to_endpoint(url, headers, query_parameters)

    text_blocks = []
    for tweet in json_response["data"]:
        author_id = tweet["author_id"]
        tweet_id = tweet["id"]
        tweet_text = tweet["text"]
        # This is wasteful as retrieves short tweets but can't work out how to filter by length of tweet in query
        text_blocks.append(generate_embed_html(author_id, tweet_id) + "\n---\n" + elongate_tweet(tweet_text))

    generate_markdown_file(text_blocks)




