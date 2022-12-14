from chatgpt_wrapper import ChatGPT
import sys

bot = ChatGPT()

for iterator in bot.ask_stream(sys.argv[1]):
    sys.stdout.write(iterator)
    sys.stdout.flush()


#response = bot.ask("Hello, world!")
#print(stream_response)  # prints the response from chatGPTR