import pytchat                                              # for reading youtube live chat                                       # data proccessing
from AikoSpeechInterface import say, start_push_to_talk     # custom tts and tts functions
from threading import Thread, Lock                          # for running concurrent loops
from random import randint                                  # for picking random comments
from time import sleep                                      # for waiting between reading comments

# Set livestream ID here
chat = pytchat.create(video_id="HERE")

to_break = False

message_lists_lock = Lock()

messages = []

# Everytime an item is added to the messages list, a bool should also be added to this list.
# If the added message is a microphone message, the bool should be True, else, it should be False.
message_priorities = [] 

#--------------------------------------- THREADED FUNCTIONS -----------------------------------------------------


def thread_listen_mic():
    """
    Starts a push to talk instance and adds speech to text generated from recorded push to talk audio to a queue list.
    """
    global messages
    global message_priorities
    global to_break

    while not to_break:
        stt = start_push_to_talk()                                              # stt: Speech to Text

        if stt != '':

            message_lists_lock.acquire()
            messages.append(stt)
            message_priorities.append(True)
            message_lists_lock.release()

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

    last_message = ''

    while chat.is_alive():

        # breaks the loop if external break condition is true

        if to_break:
            break

        # executes for every message

        for c in chat.get().sync_items():
            last_message = c.message

            message_lists_lock.acquire()
            messages.append(last_message)          # Add the new message to the list
            message_priorities.append(False)
            message_lists_lock.release()

            print(f'Added chat message to chat_list:\n{last_message}')

        # to keep CPU usage from maxing out
        sleep(0.1)


def thread_talk():
    """
    Answers messages from the queue list. Will answer any microphone messages first, in order. If no microphone messages
    are present, answers randomly selected chat messages.
    """

    global messages
    global message_priorities
    global to_break

    message_limit = 10 # determined length limit of the list containing messages

    while not to_break:

        message_lists_lock.acquire()
        if len(messages) < 1:
            message_lists_lock.release()

            # to keep CPU usage from maxing out
            sleep(0.1)
            
            continue
        message_lists_lock.release()

        message_lists_lock.acquire()
        # ------------ Mic --------------
        # will attempt to answer microphone messages
        try:
            mic_msg_index = message_priorities.index(True)
            message_priorities.pop(mic_msg_index)
            prompt = messages.pop(mic_msg_index)

            print('Picked MIC message to answer and removed it from queue:')
            print(prompt)
            say(prompt)

            message_lists_lock.release()

            sleep(0.1)
            
            continue
        except:
            pass
        # ----------- Chat --------------
        # % chance that any chat comments will be read
        chance = randint(1,100)
        if chance > 1:
            message_lists_lock.release()
            sleep(0.1)
            continue

        # deletes oldest message entries if the length limit is exceeded
        if len(messages) > message_limit:
            exceedency = len(messages) - message_limit
            print(f'Message list limit exceeded by {exceedency}. Removing old entries.')
            print(messages, '>>')
            messages = messages[exceedency : ]
            print(messages)
            message_priorities = message_priorities[exceedency : ]

        # Randomly chooses a chat message
        prompt_index = randint(0, len(messages) - 1)
        # deletes chosen message from the lists and answers it 
        message_priorities.pop(prompt_index)
        prompt = messages.pop(prompt_index)

        print(f'Picked CHAT message to answer and removed it from queue:')
        print(prompt)
        say(prompt)

        message_lists_lock.release()
        sleep(0.1)

# ---------------------------------- END OF THREADED FUNCTIONS --------------------------------------------

if __name__ == '__main__':

    # starts threads

    Thread(target=thread_listen_mic).start()

    Thread(target=thread_read_chat).start()

    Thread(target=thread_talk).start()

   #Thread(target=thread_answer_mic).start()