import pytchat

# Set livestream ID here
chat = pytchat.create(video_id="wclpOmBi5u8")

niggatext = ''
niggalist = ''

while True:
    while chat.is_alive():
        for c in chat.get().sync_items():
            print(f"{c.message}")
            niggatext = c.message
        print('here!')
        if niggatext == 'code red':
            niggatext = ''
            break
            
    # while        
    print('AIKOOOOOOOOOOOOOOOOOO')
    if niggatext == '':
        break
