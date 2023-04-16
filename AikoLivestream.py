import pytchat
from AikoSpeechInterface import listen
from AikoSpeechInterface import say
from threading import Thread
from random import randint

# Set livestream ID here
chat = pytchat.create(video_id="RWwY3NyS9jg")

prompt_list = []
to_break = False

def thread_add_chat():
    global prompt_list
    global to_break
    global chat

    message = ''

    while chat.is_alive():
        if 'code red' in message.lower():
            to_break = True
            break

        for c in chat.get().sync_items():
            message = c.message
            prompt_list.append(message)

            print(f'Added chat message to prompt_list:\n{message}')

def thread_add_mic_input():
    global prompt_list
    global to_break

    while True:
        if to_break:
            break

        mic_input = listen('Listening...', 'hey')
        if mic_input != None:
            prompt_list.append(mic_input)

            print(f'Added microphone message to prompt_list:\n{mic_input}')

def thread_read_from_list():
    global prompt_list
    global to_break

    while True:
        if to_break:
            break

        if prompt_list == []:
            continue

        prompt_index = randint(0, len(prompt_list) - 1)
        prompt = prompt_list[prompt_index]

        print(f'Selected prompt to speak:\n{prompt}')

        say(prompt)
        prompt_list.clear()
        print('Cleared prompt_list')

if __name__ == '__main__':
    Thread(target=thread_add_chat).start()
    Thread(target=thread_add_mic_input).start()
    Thread(target=thread_read_from_list).start()

