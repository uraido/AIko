from AIko import AIko

aiko = AIko('AIko', 'prompts\AIko.txt')
#aiko.change_scenario('You (Aiko) are in a roasty mood today. You have decided to roast every person that talks to you.')

message = input('Message: ')
print()
print(aiko.interact(message, True))