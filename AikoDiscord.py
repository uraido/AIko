import discord
import speech_recognition as sr
import asyncio
import os
from gtts import gTTS
from AikoSpeechInterface import modify_pitch
from AIko import *

intents = discord.Intents.all()
client = discord.Client(intents = intents)

# aiko functionality related variables

inputs_list = create_context_list()
outputs_list = create_context_list()
personality = txt_to_string('AIko.txt')
context_start = f'For context, here are our last interactions:'
log = create_log(is_summarizing = False, summary_instruction='')

# discord events

@client.event
async def on_ready():
    print('Logged in as {0.user}'.format(client))

@client.event
async def on_message(message):
    if message.content.startswith('>join'):
        if message.author.voice:
            channel = message.author.voice.channel
            voice = await channel.connect()

            print(f'Joined {channel}')
            await message.channel.send(f'Joined {channel}')
            await listen_to_voice(voice, say)

def say(text, voice):
    tts = gTTS(text=text)
    initial_file = 'speech.mp3'
    pitch_shifted_file = "mod_speech.mp3"
    tts.save(initial_file)
    modify_pitch(initial_file, pitch_shifted_file, 2.0)
    voice.play(discord.FFmpegPCMAudio(pitch_shifted_file))

async def listen_to_voice(voice, say_func):
    global inputs_list
    global outputs_list
    global personality
    global context_start
    global log

    r = sr.Recognizer()
    with sr.Microphone() as source:
        while True:
            try:

                # listens for users microphone input (not the voicechat output, as of yet)

                print('Listening...')
                audio = r.listen(source, phrase_time_limit=5)
                text = r.recognize_google(audio)
                print(f'User: {text}')

                # generates GPT completion and updates context, if text starts with keyword "aiko".

                if 'aiko' in text[:5].lower():
                    aikos_memory = update_context_string(inputs_list, outputs_list)
                    completion_request = generate_gpt_completion(
                        f'{personality} {context_start} {aikos_memory}', f"### User: {text} ### Aiko: "
                        )
                    print(f'Aiko: {completion_request[0]}')
                    say_func(completion_request[0], voice)
                    update_log(log, text, completion_request)

                    inputs_list = update_context_list(inputs_list, text)
                    outputs_list = update_context_list(outputs_list, completion_request[0])

            except sr.UnknownValueError:
                print('Google Speech Recognition could not understand audio')
            except sr.RequestError as e:
                print(f'Could not request results from Google Speech Recognition service; {e}')
            await asyncio.sleep(0.1)

client.run('MTA5MjIwNzA0ODA1MTE0NjkyMw.Gzo4yu.3abCFcmFp2J6PiQhq_mIDsbVOfYgjkXnQ_C4vw')