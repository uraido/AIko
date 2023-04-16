import pytchat
from AikoSpeechInterface import *
from threading import Thread

# Set livestream ID here
chat = pytchat.create(video_id="glOVt4XXWQs")

prompt_list = []

is_broken = False

'''
def aiko_listen_while_talking():
    global is_aiko_talking
    global is_broken
    global prompt_list

    while True:
        if is_broken:
            break
        if is_aiko_talking:
            text = listen()
            if text == None:
                continue
            if text[:3].lower() == 'hey':
                prompt_list.append(text)
                print(prompt_list)'''


# test function

def banana():
    global is_broken

    while True:
        if is_broken:
            break
        print('banana')


def aiko_read_while_talking():
    global is_aiko_talking
    global is_broken
    global prompt_list

    while chat.is_alive():
        if is_broken:
            break
        if is_aiko_talking:
            text = listen()
            if text[:3].lower() == 'hey':
                print('Updated prompt_list:')
                prompt_list.append(text)
                print(prompt_list)
            for c in chat.get().sync_items():
                print('Updated prompt_list:')
                prompt_list.append(c.message)
                print(prompt_list)

def aiko_listen():
    global prompt_list
    global is_aiko_talking
    global is_broken

    while True:
        if is_broken:
            break
        text = listen()
        if text == None:
            continue
        if is_aiko_talking:
            continue
        if text in prompt_list:
            continue
        if text[:3].lower() == 'hey':
            is_aiko_talking = True
            print('Captured microphone input:')
            print(text)
            say(text)
            is_aiko_talking = False


def aiko_read():
    global chat
    global is_aiko_talking
    global is_broken
    global prompt_list

    while chat.is_alive():
        if is_broken:
            break
        for c in chat.get().sync_items():
            if c.message.lower() == 'code red':
                is_broken = True
                print('Breaking...')
                break
            if c.message in prompt_list:
                continue
            if not is_aiko_talking:
                is_aiko_talking = True
                print('Captured chat message:')
                print(c.message)
                say(c.message)
                is_aiko_talking = False
            
        
        

if __name__ == "__main__":
    is_aiko_talking = False

    Thread(target=aiko_listen).start()
    Thread(target=aiko_read).start()
    Thread(target=aiko_read_while_talking).start()
    Thread(target=aiko_listen_while_talking).start()
    #Thread(target=banana).start()