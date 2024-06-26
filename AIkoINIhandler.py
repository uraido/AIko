'''
AIkoINIhandler.py

Parses Aikos INI configuration file and adds any missing values to avoid raising any missing value exceptions.

Changelog:
20:
- Removed a bunch of old, unused settings and sections.
- Replaced SILENCE_BREAKER section with SPONTANEOUS_TALKING section.
21:
- Fixed typo in azure_voice default value.
22:
- Added REMOTE_SIDE_PROMPTING section with server_ip and port options.
23:
- Added default_style and default_rate options to VOICE section.
24:
- Added platform option to LIVESTREAM section.
25:
- Added default_pitch option to VOICE section.
26:
- Added max_side_prompts option to GENERAL.
27:
- Added model section to GENERAL.
28:
- Added FRAME_OF_MIND section with irritability_threshold option.
29:
- Added mood_change_threshold option to FRAME_OF_MIND section.
'''

from configparser import ConfigParser
import os

def handle_ini(ini : str = 'AIkoPrefs.ini'):

    print(f'AIkoINIhandler.py: Parsing {ini}...')
    print()

    # sections the ini file should contain
    sections = [
        'GENERAL',
        'VOICE',
        'FRAME_OF_MIND',
        'SPONTANEOUS_TALKING',
        'LIVESTREAM',
        'REMOTE_SIDE_PROMPTING',
    ]

    # the options each section should contain, followed by their default values and comments.
    GENERAL = [
        ('username', 'Ulaidh'),
        ('breaker_phrase', 'code red'),
        ('dynamic_scenarios', 'True'),
        ('completion_timeout', '10'),
        ('max_side_prompts', '5'),
        ('model', 'gpt-3.5-turbo'),
    ]

    VOICE = [
        ('azure_voice', 'en-US-SaraNeural'),
        ('azure_region', 'brazilsouth'),
        ('audio_device', 'Cable Input'),
        ('mic_device', 'Cable-B Output'),
        ('default_style', 'neutral'),
        ('default_rate', '1.0'),
        ('default_pitch', '0.0'),
    ]

    FRAME_OF_MIND = [
        ('irritability_threshold', '300'),
        ('mood_change_threshold', '600'),
    ]

    SPONTANEOUS_TALKING = [
        ('min_time', '180'),
        ('max_time', '540'),
    ]

    LIVESTREAM = [
        ('platform', 'Twitch'),
        ('liveid', ''),
        ('toggle_listening', 'Page Down'),
        ('side_prompt', 'Page Up'),
        ('voice_message_expiration_time', '10.0'),
        ('chat_min_cooldown', '2'),
        ('chat_max_cooldown', '6'),
    ]

    REMOTE_SIDE_PROMPTING = [
        ('port', '5004'),
        ('server_ip', ''),
    ]

    # saves the lists containing the values in a dictionary, with their respective sections as the key
    options = {
        'GENERAL': GENERAL,
        'VOICE': VOICE,
        'FRAME_OF_MIND': FRAME_OF_MIND,
        'SPONTANEOUS_TALKING': SPONTANEOUS_TALKING,
        'LIVESTREAM': LIVESTREAM,
        'REMOTE_SIDE_PROMPTING': REMOTE_SIDE_PROMPTING,
    }

    # creates config instance
    config = ConfigParser(allow_no_value=True)

    if os.path.isfile(ini):
        # check if all sections and options are present, and if not, adds them to the file
        config.read(ini)
        for section in sections:
            if section in config:
                for key in options[section]:
                    if config.has_option(section, key[0]):
                        pass
                    else:
                        config.set(section, key[0], key[1])

            else:
                config.add_section(section)
                for key in options[section]:
                    config.set(section, key[0], key[1])

    else:
        # create config file with all keys and sections...
        for section in sections:
            config.add_section(section)
            for key in options[section]:
                config.set(section, key[0], key[1])

    with open(ini, 'w') as configfile:
        config.write(configfile)
