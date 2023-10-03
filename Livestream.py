from AIkoStreamingTools import MasterQueue, is_empty_string
import time
import AIko
import random
import socket
import pytchat
import keyboard
from pytimedinput import timedInput
from configparser import ConfigParser
from AIkoINIhandler import handle_ini
from threading import Thread
from AIkoVoice import Synthesizer, Recognizer
import os

handle_ini()
aiko = AIko.AIko('Aiko', 'prompts\AIko.txt')


def parse_msg(message: str, character: str = ':', after=False):
    '''
    Returns the contents of a string positioned after a given character.
    '''
    if after:
        return message[message.index(character) + 2:]

    return message[: message.index(character)]


# ---------------------- CONTINOUSLY THREADED FUNCTIONS ------------------
def thread_parse_chat(queue: MasterQueue, chat: pytchat.core.PytchatCore):
    last_author = None

    while chat.is_alive():
        for c in chat.get().sync_items():

            # merges current message with last message if the same user immediately follows up with a second message
            if c.author.name == last_author:
                merged_message = f'{last_message} {c.message}'
                try:
                    queue.edit_chat_message(last_message, merged_message)
                    print(f'\nMerged current message with last message added to queue:\n{last_message} + {c.message}\n')
                    last_message = merged_message

                    continue
                except ValueError:
                    print(
                        '\nAttempted message merge, but exception occurred. Message has probably been read already.\n')

            last_author = c.author.name
            last_message = f'{last_author}: {c.message}'

            queue.add_message(last_message, "chat")
            print(f'\nAdded chat message to queue:\n{last_message}\n')

        # to keep CPU usage from maxing out
        time.sleep(0.1)


def thread_speech_recognition(queue: MasterQueue, config: ConfigParser):
    username = config.get('GENERAL', 'username')
    hotkey = config.get('LIVESTREAM', 'toggle_listening')

    def parse_event(evt):
        event = str(evt)

        keyword = 'text="'
        stt_start = event.index(keyword)
        stt_end = event.index('",')

        message = event[stt_start + len(keyword):stt_end]

        if message != '':
            queue.add_message(f'{username}: {message}', "mic")
            print(f'\nAdded mic message to queue:\n{message}\n')

    # creates recognizer object for speech recognition
    recognizer = Recognizer()

    keyboard.wait(hotkey)
    print('\nEnabled speech recognition.\n')
    time.sleep(0.1)

    recognizer.start(parse_event)


def thread_spontaneus_messages(queue: MasterQueue, config: ConfigParser):
    system_prompts = AIko.txt_to_list('prompts\spontaneous_messages.txt')
    generic_messages = AIko.txt_to_list('prompts\generic_messages.txt')

    min_time = config.getint('SPONTANEOUS_TALKING', 'min_time')
    max_time = config.getint('SPONTANEOUS_TALKING', 'max_time')

    while True:
        time.sleep(random.randint(min_time, max_time))

        dice = random.randint(0, 1)
        if dice == 0:
            try:
                message = system_prompts.pop(random.randint(0, len(system_prompts) - 1))
                queue.add_message(message, "system")
                time.sleep(random.randint(min_time, max_time))
                continue
            except:
                pass

        # if dice == 1
        queue.add_message(random.choice(generic_messages), "system")


def thread_remote_side_prompt_receiver(queue: MasterQueue, config: ConfigParser):
    # ------------ Set Up ----------------
    # server_ip = '26.124.79.180'    # Ulaidh's ID (FOR RCHART TO USE)
    # server_ip = '26.246.74.120'    # Rchart's ID (FOR ULAIDH TO USE)
    # port = 5004
    server_ip = config.get('REMOTE_SIDE_PROMPTING', 'server_ip')
    port = config.getint('REMOTE_SIDE_PROMPTING', 'port')
    # ------------------------------------

    while True:

        try:
            # ------- TCP IP protocol -------
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((server_ip, port))
            msg = s.recv(1024)
            # -------------------------------

            message = msg.decode()[:-1]
            completion_option_selected = msg.decode()[-1]
            print('==========')
            print(r'Remote side prompt received with the option {}:'.format(completion_option_selected))
            print(message)
            print('==========')

            if completion_option_selected == '1':
                queue.add_message(message, "system")

            elif completion_option_selected == '2':
                aiko.add_side_prompt(message)

            else:
                print('Remote side prompt received but something went wrong. Side prompt ABORTED!')

            # disconnect the client
            s.close()
        except:
            pass
        time.sleep(0.1)


def thread_local_side_prompting(queue: MasterQueue, config: ConfigParser):
    global aiko

    breaker = config.get('GENERAL', 'breaker_phrase').lower()
    hotkey = config.get('LIVESTREAM', 'side_prompt')

    while True:
        keyboard.wait(hotkey)
        message, unused = timedInput(f"\nWrite a side prompt, or {breaker.upper()} to exit the script:\n - ", 9999)
        if breaker in message.lower():
            os._exit(0)
        option, unused = timedInput(
            f"\nPlease select an option to send the side prompt under:\n1 - Generate completion immediately\n2 - Inject information into Aiko's memory\n3 - Abort message.\n\nOption: ",
            9999)
        if option == '1':
            queue.add_message(message, "system")
        elif option == '2':
            aiko.add_side_prompt(message)


def thread_talk(queue: MasterQueue):
    global aiko

    # creates synthesizer object to voice Aiko
    synthesizer = Synthesizer()

    # creates/clears text file to display message author's name in OBS
    with open('message_author.txt', 'w') as txt:
        pass

    while True:
        msg_type, message = queue.get_next()

        if is_empty_string(message):
            continue

        output = aiko.interact(message, use_system_role=msg_type == "system")

        # reads message before answering, if message is a chat message.
        if msg_type == 'chat':
            # writes message author's name to text file to display in OBS
            with open('message_author.txt', 'w') as txt:
                txt.write('Now reading:\n')
                txt.write(f"{parse_msg(message, after=False).upper()}'s message")

            synthesizer.say(parse_msg(message, after=True), rate=random.uniform(1.2, 1.4), style="neutral")

        print()
        print(f'Aiko:{output}')
        print()

        synthesizer.say(output)

        with open('message_author.txt', 'w') as txt:
            pass

        time.sleep(0.1)


# --------------------------------------------------------------------------

msg_queue = MasterQueue()

my_config = ConfigParser()
my_config.read('AIkoPrefs.ini')

Thread(target=thread_remote_side_prompt_receiver, kwargs={'queue': msg_queue, 'config': my_config}).start()
Thread(target=thread_local_side_prompting, kwargs={'queue': msg_queue, 'config': my_config}).start()

Thread(
    target=thread_parse_chat,
    kwargs={'queue': msg_queue, 'chat': pytchat.create(video_id=my_config.get('LIVESTREAM', 'liveid'))}
        ).start()

Thread(target=thread_speech_recognition, kwargs={'queue': msg_queue, 'config': my_config}).start()
Thread(target=thread_spontaneus_messages, kwargs={'queue': msg_queue, 'config': my_config}).start()
Thread(target=thread_talk, kwargs={'queue': msg_queue}).start()

print('All threads started.')
