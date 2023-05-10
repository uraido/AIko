''' =====================================================================
AikoLivestream.py (v0.7.6)
Script for livestreaming with AIko in youtube.
Requirements:
- AikoSpeechInterface.py (4.1 or greater) and its requirements
- AIko.py (0.7.0 or greater) and its requirements
pip install:
- pytchat
- keyboard
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
0.7.4
- Updated to work with AIko070
0.7.5
- Fixed side prompting getting interrupted when messages were printed to the console.
- Implemented dynamic summarization through the evaluate_then_summarize function from AIko072 
0.7.6
- Implemented previous messages removal after Aiko picks a chat message
0.7.7
- User can now choose to immediately generate a completion when side prompting
0.7.8
- Implemented .ini configuration file
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
from random import randint                                  # for randomly choosing comments
import keyboard                                             # for hotkeys
import time                                                 # measures time for silence breaker
from pytimedinput import timedInput                         # for side prompting without interruptions

# ------------------ Set Variables -----------------
# reads config file
config = ConfigParser()
config.read('AikoPrefs.ini')

# sets variables according to config
breaker = config.get('GENERAL', 'breaker_phrase')            # to end the program. activated through microphone.
username = config.get('GENERAL', 'username')                 # the name AIko will know the microphone user as
message_limit = config.getint('LIVESTREAM', 'message_limit') # determined length limit of the list containing messages
chance = config.getint('LIVESTREAM', 'talking_chance')       # 0 no messages will be read; 100 all messages will be read
ptt_hotkey = config.get('LIVESTREAM', 'ptt_hotkey')          # push to talk hotkey
sp_hotkey = config.get('LIVESTREAM', 'sp_hotkey')            # side prompt hotkey
livestream_id = config.get('LIVESTREAM', 'liveid')           # youtube livestream ID

min_silence_breaker_time = config.getint('SILENCE_BREAKER', 'min_silence_breaker_time')
max_silence_breaker_time = config.getint('SILENCE_BREAKER', 'max_silence_breaker_time')

silence_breaker_time = randint(                              # time in seconds for silence breaker to trigger
min_silence_breaker_time,                                    
max_silence_breaker_time
)

# ------------------ Variables ---------------------
# controls loop execution
to_break = False

# starts a chat instance
chat = pytchat.create(video_id=livestream_id)

# threading locks
message_lists_lock = Lock()
side_prompt_queue_lock = Lock()
is_saying_lock = Lock()

# list which will store live chat messages
messages = []

# everytime an item is added to the messages list, a bool should also be added to this list.
# if the added message is a microphone message, the bool should be True, else, it should be False.
message_priorities = [] 

# sets strings for prompting
personality = txt_to_string('AIko.txt')
context_start = 'For context, here are our last interactions:'
sideprompt_start = 'And to keep you up to date, here are a few facts:'

# creates lists which will store context
context_list = create_context_list()
side_prompts_list = create_context_list()

# creates strings which will store context
side_prompts_string = 'EMPTY'
context_string = 'EMPTY'

# creates a log instance
log = create_log()

# saves silence breaker prompts into a list so they can be randomly chosen when silence breaker triggers
time_out_prompts = txt_to_list('silence_breaker_prompts.txt')

# side prompting variables
is_side_prompt_queued = False
queued_side_prompt = ''


#--------------------------------------- THREADED FUNCTIONS -----------------------------------------------------
def thread_hotkeys(ptt_hotkey : str = ptt_hotkey, sp_hotkey : str = sp_hotkey ):
    """
    Listens for key presses, executes code if the specified keys are pressed.

    Push to talk:
    If push to talk key is pressed, it records audio from the user's microphone and transcribes it to a string
    using whisper STT. The transcription is saved into a queue list of messages that will be fed to AIko.

    Side prompts:
    If the side prompt key is pressed, it asks for the user to write a message to be written into AIko's memory.
    The user can chose to immediately generate a completion for the written message, or to simply add it to her
    memory so that it will be added to the prompt whenever a completion is requested.
    """
    global messages
    global message_priorities
    global to_break
    global side_prompts_list
    global side_prompts_string
    global is_side_prompt_queued
    global queued_side_prompt

    while not to_break:
        # push to talk
        if keyboard.is_pressed(ptt_hotkey):
            stt = start_push_to_talk(ptt_hotkey)

            message_lists_lock.acquire()

            messages.append(stt)
            message_priorities.append(True)

            message_lists_lock.release()

            print(f'Added microphone message to mic_list:\n{stt}')

            if breaker in stt.lower():
                to_break = True

        # side prompt
        if keyboard.is_pressed(sp_hotkey):
            print("Write a side prompt to be added to Aiko's memory:")
            side_prompt, unused = timedInput(timeout = 99999)
            side_prompts_string = update_context(side_prompt, side_prompts_list)
            print('Side prompts currently in memory:')
            print(side_prompts_string)
            print('Generate completion? Y/N')
            generate_completion, unused = timedInput(timeout = 99999)

            if generate_completion.lower() == 'y':
                side_prompt_queue_lock.acquire()

                is_side_prompt_queued = True
                queued_side_prompt = side_prompt
                print('Queued side prompt for completion.')
                
                side_prompt_queue_lock.release()
                

        # to save on cpu usage
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

    # programming with threads be like:

    # message lists related variables
    global messages
    global message_priorities
    global message_limit

    global to_break

    # variables generated from user customized txt files, used for customizing prompts
    global username
    global personality

    # context related variables
    global context_list
    global context_start
    global context_string

    #chance that aiko will read a message
    global chance

    # side prompting related variables
    global side_prompts_start
    global side_prompts_string
    global is_side_prompt_queued
    global queued_side_prompt

    global log

    # time measurement starts
    t_0 = time.time()
    

    while not to_break:

        t_now = time.time()         # measures time since t0

        #---------- Side Prompt ---------
        # answers side prompt if the user choses to

        side_prompt_queue_lock.acquire()

        if is_side_prompt_queued:

            prompt = queued_side_prompt

            print('Side prompt completion requested:')
            print(prompt)

            # generates aiko's answer

            system_message = \
            f'{personality} {context_start} ### {context_string} ### {sideprompt_start} ### {side_prompts_string} ###'

            user_message = f"System: ### {prompt} ### Aiko: "

            completion_request = generate_gpt_completion(system_message, user_message)
            print(f'Aiko: {completion_request[0]}')
            
            # voices aiko's answer
            is_saying_lock.acquire()

            say(completion_request[0])

            is_saying_lock.release()

            update_log(log, prompt, completion_request, True, context_string)

            # prepares the latest interaction to be added to the context
            # (just Aiko's answer in this case, since saving the side prompt here
            # would be redundant)
            context = f'Aiko: {completion_request[0]}'

            # summarizes the latest interaction, if necessary
            context = evaluate_then_summarize(context, log)

            # updates the context with the latest interaction
            context_string = update_context(context, context_list)

            sleep(0.1)
            
            t_0 = time.time()       # restarts the timer

            is_side_prompt_queued = False

            side_prompt_queue_lock.release()

            continue

        side_prompt_queue_lock.release()

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

                # generates aiko's answer

                system_message = \
                f'{personality} {context_start} ### {context_string} ### {sideprompt_start} ### {side_prompts_string} ###'

                user_message = f"System: ### {prompt} ### Aiko: "

                completion_request = generate_gpt_completion(system_message, user_message)
                print(f'Aiko: {completion_request[0]}')
                
                # voices aiko's answer
                is_saying_lock.acquire()

                say(completion_request[0])

                is_saying_lock.release()

                update_log(log, prompt, completion_request, True, context_string)

                # prepares the latest interaction to be added to the context
                # (only with Aiko's answer in this case, since saving the time out prompt into 
                # her memory is probably a waste of tokens)

                context = f'Aiko: {completion_request[0]}'

                # summarizes the latest interaction, if necessary
                context = evaluate_then_summarize(context, log)

                # updates the context with the latest interaction
                context_string = update_context(context, context_list)

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

            # generates aiko's answer

            system_message = \
            f'{personality} {context_start} ### {context_string} ### {sideprompt_start} ### {side_prompts_string} ###'

            user_message = f"{username}: ### {prompt} ### Aiko: "

            completion_request = generate_gpt_completion(system_message, user_message)
            print(f'Aiko: {completion_request[0]}')
            
            # voices aiko's answer
            is_saying_lock.acquire()

            say(completion_request[0])

            is_saying_lock.release()

            update_log(log, prompt, completion_request, True, context_string)

            # prepares the latest interaction to be added to the context
            context = f'{username}: {prompt} | Aiko: {completion_request[0]}'

            # summarizes the latest interaction, if necessary
            context = evaluate_then_summarize(context, log)

            # updates the context with the latest interaction
            context_string = update_context(context, context_list)

            sleep(0.1)
            
            t_0 = time.time()       # restarts the timer
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

        # Picks the chosen message and his author. Then deletes it and the previous nor picked messages.
        message_lists_lock.acquire()

        prompt = messages[prompt_index][0]
        author = messages[prompt_index][1]

        messages = messages[prompt_index + 1 : ]
        message_priorities = message_priorities[prompt_index + 1 : ]


        print(f'Picked CHAT message to answer:')
        print(prompt)

        message_lists_lock.release()

        # generates aiko's answer

        system_message = \
        f'{personality} {context_start} ### {context_string} ### {sideprompt_start} ### {side_prompts_string} ###'

        user_message = f"(Live Viewer) {author}: ### {prompt} ### Aiko: "

        completion_request = generate_gpt_completion(system_message, user_message)
        print(f'Aiko: {completion_request[0]}')
        
        # voices aiko's answer
        is_saying_lock.acquire()

        say(completion_request[0])

        is_saying_lock.release()

        update_log(log, prompt, completion_request, True, context_string)

        # prepares the latest interaction to be added to the context
        context = f'(Live Viewer) {author}: {prompt} | Aiko: {completion_request[0]}'

        # summarizes the latest interaction, if necessary
        context = evaluate_then_summarize(context, log)

        # updates the context with the latest interaction
        context_string = update_context(context, context_list)

        sleep(0.1)

        t_0 = time.time()       # restarts the timer

# ---------------------------------------------------------------------------------------------------------------



if __name__ == '__main__':
    print('AikoLivestream.py: MAIN FUNCTION STARTED')
    print()

    # starts threads
    Thread(target=thread_hotkeys).start()
    print('Thread #1 started')
    Thread(target=thread_read_chat).start()
    print('Thread #2 started')
    Thread(target=thread_talk).start()
    print('Thread #3 started')
    print()
    print('ALL THREADS STARTED')
    print()