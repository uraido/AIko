import pyaudio
import wave
from pynput import keyboard
from time import sleep

# bools to keep track of key presses and the recording

key_pressed = False
done_recording = False

def on_press(key):
    global key_pressed
    global hotkey

    if not 'char' in dir(key):
        return

    if key.char != hotkey:
        return

    if not key_pressed:
    
        key_pressed = True
        print('start recording')

def on_release(key):
    global key_pressed
    global done_recording
    global hotkey

    if not 'char' in dir(key):
        return

    if key.char != hotkey:
        return

    if key_pressed:
        key_pressed = False
        done_recording = True
        print('stopped recording')

# sets and starts recording related variables

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
WAVE_OUTPUT_FILENAME = "push_to_talk.wav"
frames = []

p = pyaudio.PyAudio()
stream = p.open(format=FORMAT,channels=CHANNELS,rate=RATE,input=True,frames_per_buffer=CHUNK)

hotkey = 'p'

while True:

    # collect keyboard events

    listener = keyboard.Listener(
        on_press=on_press,
        on_release=on_release)
    listener.start()

    # saves audio frames while key is pressed

    while key_pressed:
        data = stream.read(CHUNK)
        frames.append(data)

    sleep(0.1)

    if done_recording:

        # ends audio stream

        stream.stop_stream()
        stream.close()
        p.terminate()

        # saves recording into wav file

        wf = wave.open('recording.wav', 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()

        # resets relevant variables in case user wants to make a new recording

        frames = []
        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT,channels=CHANNELS,rate=RATE,input=True,frames_per_buffer=CHUNK)

        done_recording = False
        sleep(0.1)