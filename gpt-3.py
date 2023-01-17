import os
import openai
import string
import random
from db import *
openai.api_key = os.getenv("OPENAI_API_KEY")

COMPLETIONS_MODEL = "text-davinci-003"
COMPLETIONS_API_PARAMS = {
    # We use temperature of 0.0 because it gives the most predictable, factual answer.
    "temperature": 0.0,
    "max_tokens": 300,
    "model": COMPLETIONS_MODEL,
}

# def ask_gpt_3():
#     prompt = f"{END_PROMPT}\n{message.content}"
#     response = openai.Completion.create(
#         prompt=prompt,
#         **COMPLETIONS_API_PARAMS,
#     )
#     answer = response["choices"][0]["text"].strip(" \n")
#     print(prompt)
#     print(answer)


def elongate_tweet(tweet_text):
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

    # Removing any non-printable characters before feeding to ChatGPT, not sure if required
    printable = set(string.printable)

    question_and_tweet = "{}".format(random.choice(questions)) + ''.join(filter(lambda x: x in printable, tweet_text))

    print("ChatGPT question and tweet:\n" + question_and_tweet)

    #output = bot.ask(question_and_tweet)
    output = ""
    response = openai.Completion.create(
        prompt=question_and_tweet,
        **COMPLETIONS_API_PARAMS,
    )
    answer = response["choices"][0]["text"].strip(" \n")
    return answer


if __name__ == '__main__':
    tweets = retrieve_cached_tweets()
    for tweet in tweets[:2]:
        print(elongate_tweet(tweet["text"]))

