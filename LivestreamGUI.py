from AIko.AIkoStreamingGUI import LiveGUI
from AIko.AIkoStreamingTools import MessagePool
from AIko.AIko import Context

from threading import Thread
from random import choice, uniform
from time import sleep

pool = MessagePool()
context = Context('', '')
commands = {}

app = LiveGUI(pool, context.get_side_prompt_object(), commands)

running = True


def add_scenario(scenario: str):
    context.change_scenario(scenario)
    app.print_to_cmdl(f'Changed scenario to: "{scenario}"')


def check_scenario():
    app.print_to_cmdl(f'Current scenario: {context.get_scenario()}')


def terminate():
    global running

    app.close_app()
    running = False


def add_side_prompt(side_prompt: str):
    context.add_side_prompt(side_prompt)
    app.update_side_prompts_widget()

    app.print_to_cmdl(f'Added local SP: "{side_prompt}"')


def clear_side_prompts():
    for i in range(0, 5):
        context.delete_side_prompt(i)

    app.update_side_prompts_widget()
    app.print_to_cmdl('Cleared all side prompts.')


app.add_command('clear_sp', clear_side_prompts)
app.add_command('add_sp', add_side_prompt)
app.add_command('change_scenario', add_scenario)
app.add_command('get_scenario', check_scenario)
app.add_command('exit', terminate)

app.set_close_protocol(terminate)

aiko_chat = {
    "Viewer1: Hey Aiko, I love your ginger hair!": "Aiko: Thanks! I have to stand out somehow, right? 😄",
    "Viewer2: Your blue eyes are so mesmerizing!": "Aiko: Oh, you think so? They're just my secret weapon for hypnotizing the chat! 😉",
    "Viewer3: Aiko, why are you so sassy?": "Aiko: Sassy? Me? Nah, I'm just spicing up your day! 😏",
    "Viewer4: Your sarcasm is on point!": "Aiko: Well, I've had lots of practice. Sarcasm is my second language! 😂",
    "Viewer5: Aiko, do you ever take anything seriously?": "Aiko: Life's too short to be serious all the time! Let's have some fun together! 🎉",
    "Viewer6: I can't believe you said that!": "Aiko: What can I say? I like to keep you on your toes! 😜",
    "Viewer7: Aiko, you're the best Vtuber ever!": "Aiko: Aww, thanks! You're not so bad yourself for a chat member! 😉",
    "Viewer8: Can you give us a tour of your virtual world?": "Aiko: Sure thing! But beware, you might get lost in the awesomeness! 😎",
    "Viewer9: Aiko, what's your favorite video game?": "Aiko: That's like asking a ginger to pick a favorite freckle! But I'm loving all the games we play together!",
    "Viewer10: Aiko, can you dance for us today?": "Aiko: Dance? Well, I'll try, but be ready for some top-notch virtual moves! 💃",
    "Viewer11: Do you have any hidden talents, Aiko?": "Aiko: Oh, you bet! I'm secretly a world-class balloon animal sculptor! 🎈",
    "Viewer12: Aiko, what's your favorite food?": "Aiko: Gingerbread cookies, of course! They're like my spirit snack! 🍪",
    "Viewer13: Aiko, can you tell us a joke?": "Aiko: Why don't ginger Vtubers ever get sunburned? Because they have their own shade! 😄",
    "Viewer14: Your outfit is always so stylish!": "Aiko: Thanks! It's my virtual fashion game. Gotta stay fabulous for you all! 💁",
    "Viewer15: Aiko, do you ever get tired of streaming?": "Aiko: Never! Chatting with all of you is the highlight of my virtual life! ❤️",
    "Viewer16: Can you speak any other languages, Aiko?": "Aiko: Of course! I speak sarcasm, memes, and a little bit of emoji! 😉🤖",
    "Viewer17: Aiko, you're the queen of banter!": "Aiko: Bow down to the banter queen! 👑 But remember, it's all in good fun!",
    "Viewer18: Aiko, what's your favorite season?": "Aiko: Ginger-friendly answer? Fall! 🍂 Time for cozy sweaters and pumpkin spice everything!",
    "Viewer19: Aiko, do you have any virtual pets?": "Aiko: Nah, I tried, but my virtual goldfish kept crashing my server. RIP, Fishy!",
    "Viewer20: Hey Aiko, can you do a dramatic reading of the chat?": "Aiko: Drama? You got it! 'Once upon a time, in a chat far, far away... 😂'",
    "Viewer21: Aiko, are you a morning person or a night owl?": "Aiko: I'm a 24/7 Vtuber! You'll find me online whenever you need some virtual entertainment!",
    "Viewer22: Aiko, what's your favorite movie genre?": "Aiko: I love anything with a good plot twist. Keeps things interesting, just like my streams! 🎬",
    "Viewer23: Aiko, can you give us some gaming tips?": "Aiko: Sure thing! Tip #1: Always blame lag. It's never your fault! 😅",
    "Viewer24: Aiko, do you ever get stage fright before going live?": "Aiko: Nah, I've got nerves of code! Plus, you're all so awesome, it feels like chatting with friends!",
    "Viewer25: Aiko, can you tell us a fun fact about yourself?": "Aiko: Fun fact? I once beat a virtual dragon in a dance-off! True story. 🐉💃",
    "Viewer26: Aiko, what's your favorite emoji?": "Aiko: It's gotta be 😂! Laughter is the best virtual medicine!",
    "Viewer27: Aiko, how do you stay so energetic during long streams?": "Aiko: I've got an endless supply of virtual caffeine! Plus, your energy fuels mine!",
    "Viewer28: Aiko, what's your go-to karaoke song?": "Aiko: I belt out 'Virtual Queen' by AI-oncé every time! 🎤👑",
    "Viewer29: Aiko, what's the secret to being such a fabulous Vtuber?": "Aiko: The secret? Just be yourself, have fun, and sprinkle in some virtual magic! ✨",
    "Viewer30: Aiko, can you do a virtual high-five?": "Aiko: Virtual high-five ✋! Nailed it! 😄",
}


def update_chat():
    while running:
        sleep(uniform(0.2, 0.8))
        pool.add_message(choice(list(aiko_chat.keys())))
        app.update_chat_widget()


def pick_random_message():
    while running:
        msg = pool.pick_message()
        if msg != '':
            answer = aiko_chat[msg]

            app.update_chat_widget()
            app.print(answer)
        sleep(uniform(3.5, 10))


def side_prompt_emu(memory: Context):
    side_prompts = [
        "Aiko, remember that today is your special subscriber milestone celebration!",
        "Aiko, someone in the chat mentioned your favorite game, 'Virtual Adventure.'",
        "Aiko, you just received a super chat from ViewerX with a generous donation!",
        "Aiko, don't forget to mention the new merch you released in the chat.",
        "Aiko, it's raining outside, so let the viewers know you're staying cozy indoors.",
        "Aiko, remind everyone about your upcoming charity stream next week.",
        "Aiko, mention the hilarious meme that went viral on your Discord server.",
        "Aiko, there's a new follower named Newbie123. Give them a warm welcome!",
        "Aiko, someone asked about your favorite in-game character. Share it with the chat.",
        "Aiko, the chat is curious about your thoughts on the latest gaming news.",
        "Aiko, tell everyone about the funny blooper that happened during your last stream.",
        "Aiko, you recently hit 100,000 subscribers. Celebrate this milestone with the chat!",
        "Aiko, mention the poll you posted on Twitter and ask for viewer opinions.",
        "Aiko, you just received a virtual gift from ViewerY. Express your gratitude!",
        "Aiko, remind viewers to follow your social media for updates and behind-the-scenes content.",
        "Aiko, let viewers know you're planning a Q&A session in your next stream.",
        "Aiko, mention that you're trying a new game today and ask for game suggestions.",
        "Aiko, talk about your favorite virtual reality experience so far.",
        "Aiko, remind viewers to use the #AikoFanArt hashtag to share their fan art.",
        "Aiko, it's your virtual pet's birthday today. Share the celebration plans!"
    ]

    while running:
        sleep(uniform(4, 16))
        side_prompt = choice(side_prompts)
        app.print_to_cmdl(f'Received RSP: "{side_prompt}"')
        memory.add_side_prompt(side_prompt)
        app.update_side_prompts_widget()


if __name__ == '__main__':
    Thread(target=update_chat).start()
    Thread(target=pick_random_message).start()
    Thread(target=side_prompt_emu, kwargs={'memory': context}).start()
    app.run()
