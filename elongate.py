import inspect
import requests
import string
import os
import random
import logging
import argparse
import sys
import openai
from datetime import datetime, timezone, timedelta
from mdutils.mdutils import MdUtils
from chatgpt_wrapper import ChatGPT
from db import *

openai.api_key = os.getenv("OPENAI_API_KEY")

# Parse command line arguments
parser = argparse.ArgumentParser(description="Tweet ElonGator",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-l", "--log", help="Logging Level", default="DEBUG")
parser.add_argument("-c", "--cache", help="Use Cached Tweets", default=False)
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

chatGPT = False
GPT3 = True
COMPARE = False

users_list = [
    # "ancientorigins",
    "BillGates",
    "NikkiSiapno",
    "SamRamani2",
    "oliverburkeman",
    "GordonBrown",
    # "HardcoreHistory",
    # "engineers_feed",  # The first 10 are returned in order I think?
    "sama",
    "balajis",
    "tobi",
]

questions = [
    "Can you explain this tweet: ",
    "Can you expand on this tweet: ",
    "Can you give me background on this tweet: ",
    "Can you give some context for this tweet: "
]

styles = {
    "journalisitic": "Reply as though you are writing a newspaper article",
    "scientific": "Reply acting as though you are a scientist",
}

# Twitter API


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

def retrieve_tweets(query, number_of_tweets):
    bearer_token = auth()
    headers = create_headers(bearer_token)
    query_start_time, query_end_time = generate_start_end_times(1)
    url, query_parameters = create_url(query, query_start_time, query_end_time, number_of_tweets)
    json_response = connect_to_endpoint(url, headers, query_parameters)
    return json_response


# OpenAI APIs


def elongate_tweet(text):
    # Removing any non-printable characters before feeding to ChatGPT, not sure if required
    printable = set(string.printable)

    question_and_tweet = "{}".format(random.choice(questions)) + ''.join(filter(lambda x: x in printable, text))

    logging.debug("ChatGPT question and tweet:\n" + question_and_tweet)

    #output = bot.ask(question_and_tweet)
    output = ""
    for iterator in bot.ask_stream(question_and_tweet):
        sys.stdout.write(iterator)
        sys.stdout.flush()
        output = output + iterator

    logging.debug("ChatGPT output:\n" + output)

    return output


def elongate_tweet_gpt3(text):

    COMPLETIONS_MODEL = "text-davinci-003"
    COMPLETIONS_API_PARAMS = {
        "temperature": 1.0,  # 1 means as "creative" as possible
        "max_tokens": 300,
        "model": COMPLETIONS_MODEL,
    }

    # Removing any non-printable characters before feeding to ChatGPT, not sure if required
    printable = set(string.printable)

    question_and_tweet = "{}".format(random.choice(questions)) + ''.join(filter(lambda x: x in printable, text))

    logging.debug("GPT-3 question and tweet:\n" + question_and_tweet)
    response = openai.Completion.create(
        prompt=question_and_tweet,
        **COMPLETIONS_API_PARAMS,
    )
    output = response["choices"][0]["text"].strip(" \n")
    print(output)  # This step seems to have fixed the ratelimiter, maybe need a backoff or timesleep
    return output


def elongate_tweets(tweets):
    tweets_to_elongate = [t for t in tweets["data"] if tweet_dupe_check(t["id"])]

    for tweet in tweets_to_elongate:
        tweet_text = tweet["text"]
        if chatGPT:
            # Make sure you login first using `chatgpt install`
            logging.info("Using ChatGPT Model")
            chatgpt_response = elongate_tweet(tweet_text)
            tweet["chatgpt_response"] = chatgpt_response
        elif GPT3:
            logging.info("Using GPT-3 Model")
            gpt3_response = elongate_tweet_gpt3(tweet_text)
            tweet["gpt3_response"] = gpt3_response
        elif COMPARE:
            logging.info("Using Both Models")
            gpt3_response = elongate_tweet_gpt3(tweet_text)
            chatgpt_response = elongate_tweet(tweet_text)
            tweet["gpt3_response"] = gpt3_response
            tweet["chatgpt_response"] = chatgpt_response
        else:
            logging.error("Need to set GPT3/chatGPT/COMPARE")
        store_elongated_tweet(tweet)  # Store elongated tweet in local db

# Markdown Generation


def generate_blog_frontmatter():
    date_time = datetime.today().strftime('%Y-%m-%dT%H:%M')
    date = datetime.today().strftime('%Y-%m-%d')
    front_matter = '''---
    title: "The Elon-Gator - {0}"
    date: {1}
    tagline: "Weekly Automated Elon-Gator Dump!"
    header:
      overlay_image: https://bart-parka-blog-assets.s3.eu-west-2.amazonaws.com/images/overlays/glacier.jpg
      overlay_filter: 0.3 # same as adding an opacity of 0.5 to a black background
      caption: "Photo credit: [**Bart Parka**](https://www.instagram.com/bart_parka/)"
      actions:
      - label: "See Example Code"
        url: "https://github.com/bart-parka/chatgpt-tests"
    categories:
      - blog
    tags:
      - ChatGPT
      - OpenAI
      - Twitter
      - Elon-Gator
    ---'''.format(date, date_time)
    return inspect.cleandoc(front_matter)


def generate_markdown_file():
    md_file = MdUtils(file_name='ElonGator')
    md_file.write("This post was generated automatically.")
    cached_tweets = retrieve_cached_tweets()
    for tweet in cached_tweets:
        author_id = tweet["author_id"]
        tweet_id = tweet["id"]
        md_file.new_paragraph(generate_embed_html(author_id, tweet_id) + "\n---\n")
        md_file.new_paragraph(tweet.get("chatgpt_response", "ChatGPT Response not retrieved."))
        md_file.new_paragraph(tweet.get("gpt3_response", "GPT-3 Response not retrieved."))
    md_file.write('  \n')
    md_file.create_md_file()


def prepend_blog_frontmatter(mdfile):
    with open(mdfile, 'r') as original:
        data = original.read()
    with open(mdfile, 'w') as modified:
        modified.write(generate_blog_frontmatter() + data)


if __name__ == '__main__':
    if chatGPT or COMPARE:
        bot = ChatGPT()

    tweet_query = generate_query_string(users_list)
    retrieved_tweets = retrieve_tweets(tweet_query, 10)
    elongate_tweets(retrieved_tweets)

    generate_markdown_file()
    prepend_blog_frontmatter('ElonGator.md')
