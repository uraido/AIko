'''
remote_sideprompting.py


Script that allows to send side prompts remotely to the person who is runnig the main script.
This one works as a sever in the TCP IP conecction

requirements:
	- Radmin VPN (It is necesary to do the TCP IP connection with an emulated LAN) 

'''

# ------------ Imports ---------------

import socket

# ------------------------------------



# ------------ Set Up ----------------
  
# take the server name and port name
host = 'local host'
port = 5000

# ------------------------------------


while True:
	print()
	sideprompt = input('Write a sidepromt to send: ') 

	print()
	print('Please select one option to send the prompt:')
	print('1 -Generate completion inmediately (as if it was a message to Aiko)')
	print('2 -Add the message as extra information to the next user message')
	print('3 -Abort message')

	user_option = input('option: ')
	while True:
		if (user_option == '1') or (user_option == '2') or (user_option == '3'):
			break
		print()
		print("That's not a valid option you moron, try again!")
		user_option = input('option: ')

	if user_option == '3':
		print('Message deleted!')
		continue


	# -------- TCP IP set up --------
	# create a socket at server side
	# using TCP / IP protocol
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

	# bind the socket with server
	# and port number
	s.bind(('0.0.0.0', port))

	# allow maximum 1 connection to
	# the socket
	s.listen(1)

	# wait till a client accept
	# connection
	c, addr = s.accept()

	# display client address
	#print("CONNECTION FROM:", str(addr))
	# -------------------------------


	# send message to the client after
	# encoding into binary string

	message = sideprompt + user_option
	c.send(message.encode())

	print('Message successfully sent!')
	
	# disconnect the server
	c.close()

