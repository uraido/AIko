import pyaudio
import wave
from pynput import keyboard
from time import sleep
from AikoSpeechInterface import generate_stt_whisperAPI

hotkey = 'p' # push to talk hotkey

# bools to keep track of key presses and the recording

key_pressed = False
done_recording = False

def on_press(key):
    global key_pressed
    global hotkey

    if not 'char' in dir(key):
        return

    elif key.char != hotkey:
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

    #if key.char != hotkey:
        #return

    if key_pressed:
        key_pressed = False
        done_recording = True
        print('stopped recording')

def start_push_to_talk():
    global key_pressed
    global hotkey
    global done_recording

    # sets and starts recording related variables

    CHUNK = 8192
    FORMAT = pyaudio.paInt16
    CHANNELS = 2
    RATE = 44100
    frames = []

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,channels=CHANNELS,rate=RATE,input=True,frames_per_buffer=CHUNK)

    done_recording = False

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

            # generates stt and returns it
            stt_output = generate_stt_whisperAPI('recording.wav')

            return stt_output

        sleep(0.1)

if __name__ == '__main__':
    while True:
        stt = start_push_to_talk()
        print(stt)

        if 'code red' in stt.lower():
            break