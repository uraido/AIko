import pytchat
from AikoSpeechInterface import *
from threading import Thread

# Set livestream ID here
chat = pytchat.create(video_id="3TsfnhTLvBI")

def aiko_listen():
    global is_aiko_talking

    while True:
        text = listen()
        if text == None:
            continue
        if not is_aiko_talking:
            is_aiko_talking = True
            print('Captured microphone input:')
            print(text)
            say(text)
            is_aiko_talking = False
            

def youtube_chat():
    global chat
    global is_aiko_talking

    while chat.is_alive():
        for c in chat.get().sync_items():
            if not is_aiko_talking:
                is_aiko_talking = True
                print('Captured chat message:')
                print(c.message)
                say(c.message)
                is_aiko_talking = False

if __name__ == "__main__":
    is_aiko_talking = False

    Thread(target=aiko_listen).start()
    Thread(target=youtube_chat).start()