from configparser import ConfigParser
from AIko import *
from AIkoINIhandler import handle_ini
from AIkoVoice import Synthesizer
from random import choice

handle_ini()

# gets config
config = ConfigParser()
config.read('AIkoPrefs.ini')

# creates a Synthesizer object for voicing Aiko
synthesizer = Synthesizer()

# creates an AIko object
aiko = AIko('Aiko', 'prompts\AIko.txt', open('keys/key_openai.txt').read().strip())

# enables dynamic scenario if enabled in config
dynamic_scenarios = config.getboolean('GENERAL', 'dynamic_scenarios')
if dynamic_scenarios:
    scenarios = txt_to_list('prompts\scenarios.txt')
    aiko.change_scenario(choice(scenarios))

username = config.get('GENERAL', 'username')
breaker = config.get('GENERAL', 'breaker_phrase')

spontaneous_messages = txt_to_list('prompts\spontaneous_messages.txt')

# interaction loop
while True:
    # message, timeout = timedInput(f'{username}: ', randint(60, 300))
    timeout = False
    message = input(f'{username}: ')
    use_system = False

    if timeout:
        #prompt = choice(spontaneous_messages)
        use_system = True
    elif breaker.lower() in message.lower():
        break
    else:
        prompt = f'{username}: {message}'

    output = aiko.interact(prompt, use_system)
    print(f'\nAiko:{output}\n')
    synthesizer.say(output)
