''' =====================================================================
AikoLivestream.py (v0.7)

Script for livestreaming with AIko in youtube.


Requirements:
- mpg123 installed and added to PATH var.
- ffmpeg installed and added to PATH var.
- AikoSpeechInterface.py (4.1 or greater)
- AIko.py (0.6.6 or greater)


pip install:
- pytchat
- keyboard

for Aiko:
    pip install:
    - openai
    - gtts
    - pydub
    - elevenlabslib      (if you want elevenlabs text to speech)
    - speechrecognition  (only if you want to speak to her through your mic)
    - pyaudio            (speech recognition function dependency)

    pip3 install:
    - pytimedinput 

for Speech Interface:
    pip install:
    - azure-cognitiveservices-speech



Changelog:

0.7: 
- Added versification and instalation requirements
- Now the "breaker" is defined out of the functions, in "Set Variables"
0.7.1:
- Implemented Silence Breaker
0.7.2:
- Implemented Side Prompting
0.7.3:
- Aiko will now know the username of the authors of chat comments she picks to read. Their names will also be saved in
her temporary memory with the comments.
- Added 'start statement' to be printed when the script starts.
    ===================================================================== '''

print('AikoLivestream.py: Starting...')
print()

# -------------------- Imports ---------------------

import pytchat                                              # for reading youtube live chat                                       # data proccessing
from AikoSpeechInterface import say, start_push_to_talk     # custom tts and tts functions
from threading import Thread, Lock                          # for running concurrent loops
from random import randint                                  # for picking random comments
from time import sleep                                      # for waiting between reading comments
from AIko import *                                          # AIko
from random import randint
import keyboard
import time                                                 # Meassures time for silence breaker

# --------------------------------------------------


# Set livestream ID here
chat = pytchat.create(video_id="tN8iJOrC82M")



# ------------------ Set Variables -----------------

breaker = 'code red'                                    # To end the program. Just work on Mic
patience = randint(6, 24)                               # patience
silence_breaker_time = randint(patience, 60)            # ints in which aiko is going to talk without user's input is seconds
message_limit = 10                                      # determined length limit of the list containing messages
chance = 1                                              # 0 no messages will be read; 100 all messages will be read

# --------------------------------------------------



# ------------------ Variables ---------------------
to_break = False

message_lists_lock = Lock()
is_saying_lock = Lock()

messages = []

# Everytime an item is added to the messages list, a bool should also be added to this list.
# If the added message is a microphone message, the bool should be True, else, it should be False.
message_priorities = [] 

# starts aiko functionality

username = txt_to_string('username.txt')
personality = txt_to_string('AIko.txt')
context_start = 'For context, here are our last interactions:'
sideprompt_start = 'And to keep you up to date, here are a few facts:'

inputs_list = create_context_list()
outputs_list = create_context_list()
side_prompts_list = create_context_list()

side_prompts_string = 'EMPTY'

log = create_log(is_summarizing = False, summary_instruction='')

time_out_prompts = txt_to_list('silence_breaker_prompts.txt')
# --------------------------------------------------



#--------------------------------------- THREADED FUNCTIONS -----------------------------------------------------


def thread_listen_mic():
    """
    Starts a push to talk recording instance and adds speech to text transcribed from recording to a queue list.
    """
    global messages
    global message_priorities
    global to_break
    global side_prompts_list
    global side_prompts_string

    ptt_hotkey = 'num minus' # push to talk hotkey
    sp_hotkey = 'num plus'   # side prompt hotkey

    while not to_break:
        if keyboard.is_pressed(ptt_hotkey):
            stt = start_push_to_talk(ptt_hotkey)

            message_lists_lock.acquire()

            messages.append(stt)
            message_priorities.append(True)

            message_lists_lock.release()

            print(f'Added microphone message to mic_list:\n{stt}')

            if breaker in stt.lower():
                to_break = True

        if keyboard.is_pressed(sp_hotkey):
            print("Write a side prompt to be added to Aiko's memory:")
            side_prompt = input()
            side_prompts_list = update_context_list(side_prompts_list, side_prompt)
            side_prompts_string = update_context_string_with_summaries(side_prompts_list)

            print(side_prompts_string)

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

            message_lists_lock.acquire()

            messages.append((c.message, c.author.name))          # tuple containing message and the sender's username
            message_priorities.append(False)

            message_lists_lock.release()

            print(f'Added chat message to chat_list:\n{c.message}')

        # to keep CPU usage from maxing out
        sleep(0.1)


def thread_talk():
    """
    Answers messages from the queue list. Will answer any microphone messages first, in order. If no microphone messages
    are present, answers randomly selected chat messages.
    """

    # programming with threads be like
    global messages
    global message_priorities
    global to_break
    global inputs_list
    global outputs_list
    global username
    global personality
    global context_start
    global message_limit
    global chance
    global side_prompts_start
    global side_prompts_string


    # Time messurement starts
    t_0 = time.time()
    

    while not to_break:

        t_now = time.time()         # Measures time since t0

        # -------- Empty list ----------
        # Manages when no messages are stored
        message_lists_lock.acquire()

        if len(messages) < 1:
            dt = t_now - t_0            # Calculates time passed since last interaction (delta time)

            message_lists_lock.release()

            if dt >= silence_breaker_time:
                print('Silence breaker triggered!')
                chosen_prompt = randint(0, len(time_out_prompts)  - 1)
                prompt = time_out_prompts[chosen_prompt]
                print(prompt)

                # generates aiko's answer and updates the context
                context_string = update_context_string(inputs_list, outputs_list)

                user_message = f"System: ### {prompt} ### Aiko: "
                system_message = f'{personality} {context_start} ### {context_string} ### {sideprompt_start} ### {side_prompts_string} ###'

                completion_request = generate_gpt_completion(system_message, user_message)
                print(f'Aiko: {completion_request[0]}')

                update_log(log, prompt, completion_request, context_string)

                inputs_list = update_context_list(inputs_list, prompt, 'system')
                outputs_list = update_context_list(outputs_list, completion_request[0], 'Aiko')
                
                # voices aiko's answer
                is_saying_lock.acquire()

                say(completion_request[0])

                is_saying_lock.release()

                sleep(0.1)

                t_0 = time.time()       # Reestart the timer
                continue

            # to keep CPU usage from maxing out
            sleep(0.1)
            
            continue
        
        message_lists_lock.release()

        # ------------ Mic --------------
        # will attempt to answer microphone messages
        try:
            # grabs the first microphone message in the queue
            message_lists_lock.acquire()

            mic_msg_index = message_priorities.index(True)
            message_priorities.pop(mic_msg_index)
            prompt = messages.pop(mic_msg_index)

            message_lists_lock.release()

            print('Picked MIC message to answer and removed it from queue:')
            print(prompt)

            # generates aiko's answer and updates the context
            context_string = update_context_string(inputs_list, outputs_list)

            user_message = f"{username}: ### {prompt} ### Aiko: "
            system_message = f'{personality} {context_start} ### {context_string} ### {sideprompt_start} ### {side_prompts_string} ###'

            completion_request = generate_gpt_completion(system_message, user_message)
            print(f'Aiko: {completion_request[0]}')

            update_log(log, prompt, completion_request, context_string)

            inputs_list = update_context_list(inputs_list, prompt, username)
            outputs_list = update_context_list(outputs_list, completion_request[0], 'Aiko')
            
            # voices aiko's answer
            is_saying_lock.acquire()
            say(completion_request[0])
            is_saying_lock.release()

            sleep(0.1)
            
            t_0 = time.time()       # Restarts the timer
            continue
        except:
            message_lists_lock.release()
            pass

        # ----------- Chat --------------
        # % chance that any chat comments will be read
        roll = randint(1,100)
        if roll > chance:
            sleep(0.1)
            continue


        # deletes oldest message entries if the length limit is exceeded
        message_lists_lock.acquire()

        if len(messages) > message_limit:
            exceedency = len(messages) - message_limit
            print(f'Message list limit exceeded by {exceedency}. Removing old entries.')
            print(messages, '>>')
            messages = messages[exceedency : ]
            print(messages)
            message_priorities = message_priorities[exceedency : ]

            message_lists_lock.release()

            continue

        message_lists_lock.release()

        # Randomly chooses a chat message
        message_lists_lock.acquire()

        prompt_index = randint(0, len(messages) - 1)

        message_lists_lock.release()

        # deletes chosen message from the lists and saves relevant info into variables
        message_lists_lock.acquire()

        prompt = messages[prompt_index][0]
        author = messages[prompt_index][1]

        message_priorities.pop(prompt_index)
        messages.pop(prompt_index)

        print(f'Picked CHAT message to answer and removed it from queue:')
        print(prompt)

        message_lists_lock.release()

        # request aiko's answer and updates context
        context_string = update_context_string(inputs_list, outputs_list)

        user_message = f"(Chat user) {author}: ### {prompt} ### Aiko: "
        system_message = f'{personality} {context_start} ### {context_string} ### {sideprompt_start} ### {side_prompts_string} ###'

        completion_request = generate_gpt_completion(system_message, user_message)
        print(f'Aiko: {completion_request[0]}')

        update_log(log, prompt, completion_request, context_string)

        inputs_list = update_context_list(inputs_list, prompt, f'(Chat user) {author}')
        outputs_list = update_context_list(outputs_list, completion_request[0], 'Aiko')

        # voices aiko's answer
        is_saying_lock.acquire()

        say(completion_request[0])

        is_saying_lock.release()

        sleep(0.1)

        t_0 = time.time()       # Restarts the timer


# ---------------------------------- END OF THREADED FUNCTIONS --------------------------------------------



if __name__ == '__main__':
    print('AikoLivestream.py: MAIN FUNCTION STARTED')
    print()

    # starts threads
    Thread(target=thread_listen_mic).start()
    print('Thread #1 started')
    Thread(target=thread_read_chat).start()
    print('Thread #2 started')
    Thread(target=thread_talk).start()
    print('Thread #3 started')
    print()
    print('ALL THREADS STARTED')
    print()