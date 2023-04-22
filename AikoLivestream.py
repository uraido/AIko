import pytchat                                   # for reading youtube live chat
from AikoSpeechInterface import listen, say      # custom tts and tts functions
from threading import Thread, Lock               # for running concurrent loops
from random import randint                       # for picking random comments
from time import sleep                           # for waiting between reading comments
from my_push_to_talk import start_push_to_talk   # push to talk

# Set livestream ID here
chat = pytchat.create(video_id="IM11btB1OwY")

chat_list = []
mic_list = []

to_break = False

chat_list_lock = Lock()
mic_list_lock = Lock()
is_saying_lock = Lock()

#--------------------------------------- THREADED FUNCTIONS -----------------------------------------------------

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

        # breaks the loop if external break condition is true

        if to_break:
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

        # to keep CPU usage from maxing out
        sleep(0.1)

def thread_push_to_talk():
    """
    Starts a push to talk instance and adds speech to text generated from recorded push to talk audio to a queue list.
    """

    global mic_list
    global to_break

    while not to_break:
        stt = start_push_to_talk()

        if stt != '':

            mic_list_lock.acquire()
            mic_list.append(stt)
            mic_list_lock.release()

            print(f'Added microphone message to mic_list:\n{stt}')

        if 'code red' in stt.lower():
            to_break = True

        # to keep cpu usage from maxing out
        sleep(0.1)

def thread_answer_chat(): # UNUSED. REFER TO "PUSH TO TALK LOOP" IN MAIN INSTEAD.
    """
    Pops (removes) a random message from the chat queue list and then answers it, then sleeps for a random
    amount of time in seconds. If there are microphone messages on the mic queue, waits until all microphone
    messages have been cleared before going back to answering chat messages.
    """

    global chat_list
    global mic_list
    global to_break

    while not to_break:

        chat_list_lock.acquire()
        if chat_list == []:
            chat_list_lock.release()

            # to keep CPU usage from maxing out
            sleep(0.1)
            
            continue
        chat_list_lock.release()
        
        mic_list_lock.acquire()
        if mic_list != []:
            mic_list_lock.release()

            # to keep CPU usage from maxing out
            sleep(0.1)
            
            continue
        mic_list_lock.release()

        chat_list_lock.acquire()
        prompt_index = randint(0, len(chat_list) - 1)
        prompt = chat_list.pop(prompt_index)
        chat_list_lock.release()

        is_saying_lock.acquire()
        print(f'\nSelected CHAT prompt to answer:\n{prompt}\nRemoved it from queue.')
        say(prompt)
        is_saying_lock.release()


        # Time AIko will wait before reading any other chat messages, when reading from chat is possible.
        #sleep(randint(1, 90))
        sleep(0.1)

def thread_answer_mic():
    """
    Answers queued microphone messages, in order.
    """
    global mic_list
    global to_break

    while not to_break:

        mic_list_lock.acquire()
        if mic_list == []:
            mic_list_lock.release()

            # to keep CPU usage from maxing out
            sleep(0.1)

            continue
        mic_list_lock.release()

        mic_list_lock.acquire()
        prompt = mic_list.pop(0)
        mic_list_lock.release()

        is_saying_lock.acquire()
        print(f'\nSelected MIC prompt to answer:\n{prompt}\nRemoved it from queue.')
        say(prompt)
        is_saying_lock.release()

        # to keep CPU usage from maxing out
        sleep(0.1)

# ---------------------------------- END OF THREADED FUNCTIONS --------------------------------------------

if __name__ == '__main__':

    # starts threads

    Thread(target=thread_update_chat_list).start()

    #Thread(target=thread_push_to_talk).start()

    Thread(target=thread_answer_chat).start()

    Thread(target=thread_answer_mic).start()

    # push to talk loop

    while not to_break:
        stt = start_push_to_talk()

        if stt != '':

            mic_list_lock.acquire()
            mic_list.append(stt)
            mic_list_lock.release()

            print(f'Added microphone message to mic_list:\n{stt}')

        if 'code red' in stt.lower():
            to_break = True

        # to keep cpu usage from maxing out
        sleep(0.1)