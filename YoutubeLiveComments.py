import pytchat
from AikoSpeechInterface import *
from threading import Thread

# Set livestream ID here
chat = pytchat.create(video_id="glOVt4XXWQs")

prompt_list = []

is_broken = False


def aiko_listen():
    global prompt_list
    global is_aiko_talking

    while True:
        if is_broken:
            break
        text = listen()
        if text == None:
            continue
        if is_aiko_talking:
            continue
        else:
            if text[:3].lower() == 'hey':
                prompt_list.append(text)
                print(prompt_list)
        if text[:3].lower() == 'hey':
            is_aiko_talking = True
            print('Captured microphone input:')
            print(text)
            say(text)
            is_aiko_talking = False


def youtube_chat():
    global chat
    global is_aiko_talking
    global prompt_list
    global is_broken

    while chat.is_alive():
        if is_broken:
            break
        for c in chat.get().sync_items():
            if c.message.lower() == 'code red':
                is_broken = True
                break
            if not is_aiko_talking:
                is_aiko_talking = True
                print('Captured chat message:')
                print(c.message)
                say(c.message)
                is_aiko_talking = False
            else:
                prompt_list.append(c.message)
                print(prompt_list)
            
        
        

if __name__ == "__main__":
    is_aiko_talking = False

    Thread(target=aiko_listen).start()
    Thread(target=youtube_chat).start()