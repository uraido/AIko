import pytchat
from AikoSpeechInterface import listen, say
from threading import Thread
from random import randint
from time import sleep

# Set livestream ID here
chat = pytchat.create(video_id="ID HERE")

chat_list = []
mic_list = []
to_break = False
is_saying = False

def thread_update_chat_list():
    """
    Adds chat messages to a queue list. Removes the first item from the list if the length limit is reached.
    """

    global chat_list
    global to_break
    global chat

    chat_list_length_limit = 10
    message = ''

    while chat.is_alive():
        if 'code red' in message.lower():
            to_break = True
            break

        for c in chat.get().sync_items():
            message = c.message

            if len(chat_list) > chat_list_length_limit:
                chat_list = chat_list[1:]
                print(f'chat_list length has surpassed {chat_list_length_limit}. First item was removed.')

            chat_list.append(message)
            print(f'Added chat message to chat_list:\n{message}')

def thread_update_mic_list():
    """
    Adds microphone messages to a queue list.
    """

    global mic_list
    global to_break

    while not to_break:

        mic_input = listen('Listening...', 'hey')

        if mic_input != None:

            mic_list.append(mic_input)
            print(f'Added microphone message to mic_list:\n{mic_input}')

def thread_answer_chat():
    """
    Pops (removes) a random message from the chat queue list and then answers it, then sleeps for a random
    amount of time in seconds. If there are microphone messages on the mic queue, waits until all microphone
    messages have been cleared before going back to answering chat messages.
    """

    global chat_list
    global mic_list
    global to_break
    global is_saying

    while not to_break:

        if chat_list == []:
            continue

        if mic_list != []:
            continue

        if is_saying:
            continue


        is_saying = True

        prompt_index = randint(0, len(chat_list) - 1)
        prompt = chat_list.pop(prompt_index)
        print(f'\nSelected CHAT prompt to answer:\n{prompt}')

        say(prompt)
        print('Removed selected chat prompt from chat_list.')

        is_saying = False

        # Time AIko will wait before reading any other chat messages, when reading from chat is possible.
        sleep(randint(1, 90))

def thread_answer_mic():
    """
    Answers queued microphone messages, in order.
    """
    global mic_list
    global to_break
    global is_saying

    while not to_break:

        if mic_list == []:
            continue

        if is_saying:
            continue

        is_saying = True

        prompt = mic_list.pop(0)
        print(f'\nSelected MIC prompt to answer:\n{prompt}')

        say(prompt)
        print('Removed selected prompt from mic_list.')

        is_saying = False

if __name__ == '__main__':

    Thread(target=thread_update_chat_list).start()
    Thread(target=thread_update_mic_list).start()

    Thread(target=thread_answer_chat).start()
    Thread(target=thread_answer_mic).start()