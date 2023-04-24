import pytchat                                   # for reading youtube live chat
import pandas as pd                              # data proccessing
from AikoSpeechInterface import listen, say      # custom tts and tts functions
from threading import Thread, Lock               # for running concurrent loops
from random import randint                       # for picking random comments
from time import sleep                           # for waiting between reading comments
from my_push_to_talk import start_push_to_talk   # push to talk

# Set livestream ID here
chat = pytchat.create(video_id="YmHvLcr1uDs")

chat_list = []
mic_list = []

to_break = False

message_list_lock = Lock()

messages = pd.DataFrame(columns = ['Source', 'Message'])

#--------------------------------------- THREADED FUNCTIONS -----------------------------------------------------


def thread_listen_mic():
    """
    Starts a push to talk instance and adds speech to text generated from recorded push to talk audio to a queue list.
    """
    global messages
    global to_break

    while not to_break:
        stt = start_push_to_talk()                                              # stt: Speech to Text

        if stt != '':

            message_list_lock.acquire()
            messages.loc[len(messages.index)] = ['Mic', stt]                    # Add the new message to the list
            #mic_list.append(stt)
            message_list_lock.release()

            print(f'Added microphone message to mic_list:\n{stt}')

        if 'code red' in stt.lower():
            to_break = True

        # to keep cpu usage from maxing out
        sleep(0.1)



def thread_read_chat():
    """
    Adds chat messages to a queue list. Removes the first item (oldest item) from the list if the length
    limit is reached.
    """

    global messages
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

        message_list_lock.acquire()
        # if len(messages) > chat_list_length_limit:

        #     exceeding_entries_count = len(messages) - chat_list_length_limit
        #     print(f'chat_list exceeding limit by {exceeding_entries_count}:', chat_list)    
        #     chat_list = chat_list[exceeding_entries_count : ]
        #     print('corrected chat_list:', chat_list)

        #     print(f'chat_list has surpassed the entry limit of {chat_list_length_limit}\nExceeding old entries have been removed.')
        message_list_lock.release()

        # executes for every message.

        for c in chat.get().sync_items():
            last_message = c.message

            message_list_lock.acquire()
            messages.loc[len(messages.index)] = ['Chat', last_message]          # Add the new message to the list
            message_list_lock.release()

            print(f'Added chat message to chat_list:\n{last_message}')

        # to keep CPU usage from maxing out
        sleep(0.1)


def thread_talk():
    """
    Removes a random message from the chat queue list and then answers it, then sleeps for a random
    amount of time in seconds. If there are microphone messages on the mic queue, waits until all microphone
    messages have been cleared before going back to answering chat messages.
    """

    global messages
    global to_break

    while not to_break:

        message_list_lock.acquire()
        if len(messages) == 0:
            message_list_lock.release()

            # to keep CPU usage from maxing out
            sleep(0.1)
            
            continue
        message_list_lock.release()

        message_list_lock.acquire()

        # ------------ Mic --------------
        if len(messages.loc[messages['Source'] == 'Mic']['Source']) > 0:
            prompt = messages.loc[messages['Source'] == 'Mic']['Message'].values[0]           # Picks the first message from Mic
            messages = messages[messages['Message'] != prompt]                                 # Deletes the message from the df
            say(prompt)
            print(f'\nSelected MIC prompt to answer:\n{prompt}\nRemoved it from queue.')

            message_list_lock.release()
            sleep(0.1)
            continue

        # ----------- Chat --------------
        prompt_index = randint(0, len(messages.loc[messages['Source'] == 'Chat']['Source']) - 1)                                         # Random to pick a message
        prompt = messages.loc[messages['Source'] == 'Chat']['Message'].values[prompt_index]   # Picks the first message from Chat
        # hard shit, we have to delete all previous messages. For now, just gonna delete the current one
        messages = messages[messages['Message'] != prompt]
        say(prompt)
        print(f'\nSelected CHAT prompt to answer:\n{prompt}\nRemoved it from queue.')

        message_list_lock.release()
        sleep(0.1)
        
    








# ---------------------------------- END OF THREADED FUNCTIONS --------------------------------------------

if __name__ == '__main__':

    # starts threads

    Thread(target=thread_listen_mic).start()

    Thread(target=thread_read_chat).start()

    Thread(target=thread_talk).start()

   #Thread(target=thread_answer_mic).start()