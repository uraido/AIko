import pytchat
from AikoSpeechInterface import listen
from AikoSpeechInterface import say
from threading import Thread
from random import randint
from time import sleep

# Set livestream ID here
chat = pytchat.create(video_id="RWwY3NyS9jg")

chat_list = []
mic_list = []
to_break = False
is_saying = False

def thread_update_chat_list():
    """
    Adds chat messages to a queue list.
    """

    global chat_list
    global to_break
    global chat

    message = ''

    while chat.is_alive():
        if 'code red' in message.lower():
            to_break = True
            break

        for c in chat.get().sync_items():
            message = c.message
            chat_list.append(message)

            print(f'Added chat message to chat_list:\n{message}')

def thread_update_mic_list():
    """
    Adds microphone messages to a queue list.
    """

    global mic_list
    global to_break

    while True:
        if to_break:
            break

        mic_input = listen('Listening...', 'hey')
        if mic_input != None:
            mic_list.append(mic_input)

            print(f'Added microphone message to mic_list:\n{mic_input}')

def thread_answer_chat():
    """
    Will pick a random chat message from the queue. If there are microphone messages on the mic queue, will wait until
    all microphone messages on queue have been cleared before going back to reading chat messages.
    """

    global chat_list
    global mic_list
    global to_break
    global is_saying

    while True:

        if to_break:
            break

        if chat_list == []:
            continue

        if mic_list != []:
            continue

        if is_saying:
            continue


        is_saying = True
        prompt_index = randint(0, len(chat_list) - 1)
        prompt = chat_list[prompt_index]

        print(f'\nSelected CHAT prompt to answer:\n{prompt}')

        say(prompt)
        chat_list.clear()
        print('Cleared chat_list')
        is_saying = False

        # Time AIko will wait before reading any other chat messages, when reading from chat is possible.
        sleep(randint(1, 10))

def thread_answer_mic():
    global mic_list
    global to_break
    global is_saying

    while True:
        if to_break:
            break

        if mic_list == []:
            continue

        if is_saying:
            continue

        is_saying = True
        prompt_index = randint(0, len(mic_list) - 1)
        prompt = mic_list[prompt_index]

        print(f'\nSelected MIC prompt to answer:\n{prompt}')

        say(prompt)
        mic_list.clear()
        print('Cleared mic_list')
        is_saying = False

if __name__ == '__main__':
    Thread(target=thread_update_chat_list).start()
    Thread(target=thread_update_mic_list).start()
    Thread(target=thread_answer_chat).start()
    Thread(target=thread_answer_mic).start()

