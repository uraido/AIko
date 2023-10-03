"""
GUI interaction loop for livestreaming.

Requirements:

.py:
- AIko.py (156beta or greater) and its requirements.
- AIkoINIHandler.py (24 or greater).
- AIkoStreamingGUI.py (015 or greater).
- AIkoStreamingTools.py (029 or greater).
- AIkoVoice.py (115 or greater) and its requirements.

packages:
- pip install pytchat

Changelog:

001:
- Initial release.
"""
import os
import socket
from time import sleep
from threading import Thread, Event
from configparser import ConfigParser
from random import choice, uniform, randint

import pytchat

from AIko import AIko, txt_to_list
from AIkoStreamingGUI import LiveGUI
from AIkoINIhandler import handle_ini
from AIkoVoice import Synthesizer, Recognizer
from AIkoStreamingTools import MasterQueue, Pytwitch

handle_ini()

# main objects
aiko = AIko('Aiko', 'prompts/AIko.txt')
master_queue = MasterQueue()
app = LiveGUI(master_queue, aiko)

# config
config = ConfigParser()
config.read('AikoPrefs.ini')

# loop controller
running = True

# threading events
mute_event = Event()
allow_spontaneous = Event()
# ---------------------------------------- COMMAND LINE COMMAND FUNCTIONS ----------------------------------------------


def cmd_toggle_mic():
    mute_event.set()


# not a cmdl command, sets the function to be called when the mute button is pressed
app.bind_mute_button(cmd_toggle_mic)


def cmd_unpause_spontaneous():
    allow_spontaneous.set()
    app.print_to_cmdl('Resumed spontaneous messages.')


app.add_command('unpause_spon', cmd_unpause_spontaneous)


def cmd_pause_spontaneous():
    allow_spontaneous.clear()
    app.print_to_cmdl('Spontaneous messages will be paused after next message.')


app.add_command('pause_spon', cmd_pause_spontaneous)


def cmd_check_spontaneous():
    if allow_spontaneous.is_set():
        app.print_to_cmdl('Spontaneous messages are currently: UNPAUSED.')
    else:
        app.print_to_cmdl('Spontaneous messages are currently: PAUSED.')


app.add_command('check_spon', cmd_check_spontaneous)


def cmd_switch_scenario(scenario: str):
    aiko.change_scenario(scenario)
    app.print_to_cmdl('Changed scenario.')


app.add_command('switch_scenario', cmd_switch_scenario)


def cmd_check_scenario():
    app.print_to_cmdl(f'Current scenario: {aiko.check_scenario()}')


app.add_command('check_scenario', cmd_check_scenario)


def add_side_prompt(side_prompt: str):
    aiko.add_side_prompt(side_prompt)
    app.update_side_prompts_widget()

    app.print_to_cmdl(f'Added local SP: "{side_prompt}"')


app.add_command('add_sp', add_side_prompt)


def cmd_clear_side_prompts():
    for i in range(0, 5):
        aiko.delete_side_prompt(i)

    app.update_side_prompts_widget()
    app.print_to_cmdl('Cleared all side prompts.')


app.add_command('clear_sp', cmd_clear_side_prompts)


def cmd_send_sys_message(message: str):
    master_queue.add_message(message, "system")
    app.print_to_cmdl(f'Added SM to queue: "{message}"')


app.add_command('send_sys_msg', cmd_send_sys_message)


def cmd_close_protocol():
    global running

    running = False
    app.close_app()
    os._exit(0)


app.add_command('exit', cmd_close_protocol)
# also sets this function to run when the app is closed
app.set_close_protocol(cmd_close_protocol)


# ---------------------------------------- CONTINUOUSLY THREADED FUNCTIONS ---------------------------------------------


def thread_chat_twitch():
    global running

    # starts pytwitch object
    chat = Pytwitch(open('keys/key_twitch.txt').read().strip(), "aikochannel")
    # last author variable for merging messages
    last_author = None

    while running:
        # blocks until a message is received
        author, message = chat.get_message()
        # merges current message with last message if the same user immediately follows up with a second message
        if author == last_author:
            merged_message = f'{last_message} {message}'
            try:
                master_queue.edit_chat_message(last_message, merged_message)
                app.print_to_cmdl(f'Merge triggered: {last_message} + {message}')
                last_message = merged_message

                app.update_chat_widget()
                continue
            except ValueError:
                app.print_to_cmdl('Attempted merge, but exception occurred.')

        last_author = author
        last_message = f'{last_author}: {message}'

        # adds message to queue
        master_queue.add_message(last_message, "chat")

        app.update_chat_widget()
        # print_to_cmdl(f'\nAdded chat message to queue:\n{last_message}\n')

        # to keep CPU usage from maxing out
        sleep(0.1)


def thread_chat_youtube(chat: pytchat.core.PytchatCore):
    global running
    last_author = None

    while chat.is_alive():
        for c in chat.get().sync_items():
            # merges current message with last message if the same user immediately follows up with a second message
            if c.author.name == last_author:
                merged_message = f'{last_message} {c.message}'
                try:
                    master_queue.edit_chat_message(last_message, merged_message)
                    app.print_to_cmdl(f'Merge triggered: {last_message} + {c.message}')
                    last_message = merged_message

                    continue
                except ValueError:
                    app.print_to_cmdl('Attempted merge, but exception occurred.')

            last_author = c.author.name
            last_message = f'{last_author}: {c.message}'

            # adds message to queue
            master_queue.add_message(last_message, "chat")

            app.update_chat_widget()

        # to keep CPU usage from maxing out
        sleep(0.1)


def thread_remote_receiver():
    global running
    # ------------ Set Up ----------------
    # server_ip = '26.124.79.180'    # Ulaidh's ID (FOR RCHART TO USE)
    # server_ip = '26.246.74.120'    # Rchart's ID (FOR ULAIDH TO USE)
    # port = 5004
    server_ip = config.get('REMOTE_SIDE_PROMPTING', 'server_ip')
    port = config.getint('REMOTE_SIDE_PROMPTING', 'port')
    # ------------------------------------

    while running:

        try:
            # ------- TCP IP protocol -------
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((server_ip, port))
            msg = s.recv(1024)
            # -------------------------------

            message = msg.decode()[:-1]
            completion_option_selected = msg.decode()[-1]
            app.print_to_cmdl(
                f'Remote side prompt received with the option {completion_option_selected}: {message}'
                )

            if completion_option_selected == '1':
                master_queue.add_message(message, "system")

            elif completion_option_selected == '2':
                aiko.add_side_prompt(message)
                app.update_side_prompts_widget()

            else:
                app.print_to_cmdl('Remote side prompt received but something went wrong. Side prompt ABORTED!')

            # disconnect the client
            s.close()
        except:
            pass
        sleep(0.1)


def thread_speech_recognition():
    username = config.get('GENERAL', 'username')

    def parse_event(evt):
        event = str(evt)

        keyword = 'text="'
        stt_start = event.index(keyword)
        stt_end = event.index('",')

        message = event[stt_start + len(keyword):stt_end]

        if message != '':
            master_queue.add_message(f'{username}: {message}', "mic")
            app.print_to_cmdl(f'Added mic message to queue: {message}')

    # creates recognizer object for speech recognition
    recognizer = Recognizer()

    mute_event.wait()
    mute_event.clear()
    # print('\nEnabled speech recognition.\n')
    sleep(0.1)

    recognizer.start(parse_event, mute_event)


def thread_spontaneous_messages():
    system_prompts = txt_to_list('prompts\spontaneous_messages.txt')
    generic_messages = txt_to_list('prompts\generic_messages.txt')

    min_time = config.getint('SPONTANEOUS_TALKING', 'min_time')
    max_time = config.getint('SPONTANEOUS_TALKING', 'max_time')
    allow_spontaneous.set()

    while running:
        # executes if spontaneous messages arent paused
        allow_spontaneous.wait()

        # waits for random amount of time
        sleep(randint(min_time, max_time))
        # decides between spontaneous or generic message
        dice = randint(0, 1)
        if dice == 0:
            try:
                message = system_prompts.pop(randint(0, len(system_prompts) - 1))
                master_queue.add_message(message, "system")
                sleep(randint(min_time, max_time))
                continue
            except:
                pass

        # if dice == 1
        master_queue.add_message(choice(generic_messages), "system")


def thread_talk():
    # to parse messages before voicing
    def parse_msg(msg: str, character: str = ':', after=False):

        if after:
            return msg[msg.index(character) + 2:]

        return msg[: msg.index(character)]

    # creates synthesizer object to voice Aiko
    synthesizer = Synthesizer()

    # creates/clears text file to display message author's name in OBS
    with open('message_author.txt', 'w') as txt:
        pass

    while True:
        msg_type, message = master_queue.get_next()
        if msg_type == 'chat':
            app.update_chat_widget()

        if message == '':
            continue

        output = aiko.interact(message, use_system_role=msg_type == "system")

        # reads message before answering, if message is a chat message.
        if msg_type == 'chat':
            # writes message author's name to text file to display in OBS
            with open('message_author.txt', 'w') as txt:
                txt.write('Now reading:\n')
                txt.write(f"{parse_msg(message, after=False).upper()}'s message")

            synthesizer.say(parse_msg(message, after=True), rate=uniform(1.2, 1.4), style="neutral")

        app.print(f'({msg_type.upper()}) {message}')
        app.print(f'Aiko: {output}\n')

        synthesizer.say(output)

        with open('message_author.txt', 'w') as txt:
            pass

        sleep(0.1)

# ----------------------------------------------------------------------------------------------------------------------


platform = config.get('LIVESTREAM', 'platform').lower()

if platform == 'twitch':
    Thread(target=thread_chat_twitch).start()
elif platform == 'youtube':
    yt_chat = pytchat.create(video_id=config.get('LIVESTREAM', 'liveid'))
    Thread(target=thread_chat_youtube, kwargs={'chat': yt_chat}).start()

Thread(target=thread_remote_receiver).start()
Thread(target=thread_speech_recognition).start()
Thread(target=thread_spontaneous_messages).start()
Thread(target=thread_talk).start()
app.run()
