import pytchat
from AikoSpeechInterface import listen, say
from threading import Thread, Lock
from random import randint
from time import sleep

# Set livestream ID here
chat = pytchat.create(video_id="d_Koe8olEVE")

chat_list = []
mic_list = []

to_break = False
is_saying = False

chat_list_lock = Lock()

def thread_update_chat_list():
    """
    Adds chat messages to a queue list. Removes the first item (oldest item) from the list if the length
    limit is reached.
    """

    global chat_list
    global to_break
    global chat

    chat_list_length_limit = 10
    last_message = ''

    while chat.is_alive():

        # breaks this loop if the defined string is read from youtube chat and sets a variable to turn off the loops
        # in the other threads.

        if 'code red' in last_message.lower():
            to_break = True
            break
        
        # code below tries to keep chat_list's number of items under the defined chat_list_length_limit.
        # the lock is necessary to prevent this function from removing items from the list while 
        # thread_answer_chat() is controlling it, among other issues that can occur when multiple
        # threads try to modify the same variable.

        chat_list_lock.acquire()
        if len(chat_list) > chat_list_length_limit:

            exceeding_entries_count = len(chat_list) - chat_list_length_limit
            print(f'chat_list exceeding limit by {exceeding_entries_count}:', chat_list)    
            chat_list = chat_list[exceeding_entries_count : ]
            print('corrected chat_list:', chat_list)

            print(f'chat_list has surpassed the entry limit of {chat_list_length_limit}\nExceeding old entries have been removed.')
        chat_list_lock.release()

        # executes for every message sent in the youtube chat.

        for c in chat.get().sync_items():
            last_message = c.message

            chat_list_lock.acquire()
            chat_list.append(last_message)
            chat_list_lock.release()

            print(f'Added chat message to chat_list:\n{last_message}')

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

        chat_list_lock.acquire()
        if chat_list == []:
            chat_list_lock.release()
            continue
        chat_list_lock.release()
        
        if mic_list != []:
            continue
        
        if is_saying:
            continue

        is_saying = True

        chat_list_lock.acquire()

        prompt_index = randint(0, len(chat_list) - 1)
        prompt = chat_list.pop(prompt_index)

        chat_list_lock.release()

        print(f'\nSelected CHAT prompt to answer:\n{prompt}\nRemoved it from queue.')

        say(prompt)

        is_saying = False

        # Time AIko will wait before reading any other chat messages, when reading from chat is possible.
        #sleep(randint(1, 90))

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