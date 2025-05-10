from telethon import TelegramClient
# # import pandas as pd
# import json 
# from pathlib import Path
# import json
# import os
# import asyncio

# # from config import Config # import the api id, hash from here
# # You can test the code by inputing your cridentials and uncommenting
# # Ideally dont hardcode it here
# # api_id = Config.api_id
# # api_hash = Config.api_hash

from dotenv import load_dotenv
import os
from os.path import join, dirname

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

SECRET_KEY = os.environ.get("SECRET_KEY")
DATABASE_PASSWORD = os.environ.get("DATABASE_PASSWORD")


api_id = os.environ.get("TELEGRAM_API_ID")
api_hash = os.environ.get("TELEGRAM_API_HASH")
# session_name = os.environ.get("TELEGRAM_SESSION_NAME")

# # # Get credentials from the Config.py file 
# # api_id = Config.api_id
# # api_hash = Config.api_hash

# # # This is the name of the session file that will be created and stored in the working directory. Session files are used to store the state of the client, so that it can be resumed later so you dont have to login everytime you run the code
# # session_name = Config.session_name


# # Make a coroutine main()
# # This function/coroutine takes in 
# #  1. the name of the chat we want to collect 
# #  2. the number of messages to collect 
# # There are many other arguments you can pass (https://docs.telethon.dev/en/stable/modules/client.html?

# async def main(chat_name, limit):
#     # "async with" creates asynchronous context managers
#     # It is an extension of the "with" expression for use only in coroutines within asyncio programs
#     async with TelegramClient(session_name, api_id, api_hash) as client:
        
#         # Get chat info 
#         chat_info = await client.get_entity(chat_name)
        
#         # Get all the messages, given the limit
#         # It will return the latest 5 messages if limit is 5
#         messages = await client.get_messages(entity=chat_info, limit=limit)
        
#         # return the results in a dictionary
#         return ({"messages": messages, "channel": chat_info})



# # limit=None will collect all the messages from nytimes Telegram channel (https://t.me/nytimes)
# # This open an input box and ask you to input your phone number 
# #  
# chat_input = "nytimes"
# results = asyncio.run(main(chat_name = chat_input, limit=5)) 

# # Print the results
# print(results["messages"][0].to_dict())


# The first parameter is the .session file name (absolute paths allowed)
# with TelegramClient('anon', api_id, api_hash) as client:
#     client.loop.run_until_complete(client.send_message('me', 'perfect'))

# from telethon import TelegramClient, events

# client = TelegramClient('anon', api_id, api_hash)

# @client.on(events.NewMessage)
# async def my_event_handler(event):
#     if 'hello' in event.raw_text:
#         await event.reply('hi!')

# client.start()
# client.run_until_disconnected()


async def main(chat_name, limit):
    # "async with" creates asynchronous context managers
    # It is an extension of the "with" expression for use only in coroutines within asyncio programs
    async with TelegramClient('./sessions_cache/anon', api_id, api_hash) as client:
        
        # Get chat info 
        chat_info = await client.get_entity(chat_name)
        
        # Get all the messages, given the limit
        # It will return the latest 5 messages if limit is 5
        messages = await client.get_messages(entity=chat_info, limit=limit)
        
        print(messages)

        # return the results in a dictionary
        return ({"messages": messages, "channel": chat_info})


async def count_seconds():
    import asyncio
    seconds = 0
    while True:
        await asyncio.sleep(1)
        seconds += 1
        if seconds % 3 == 0:
            print(f"{seconds} seconds have passed.")


import asyncio

async def run_both():
    # Run both main and count_seconds concurrently
    await asyncio.gather(
        main("me", None),
        count_seconds()
    )

asyncio.run(run_both())