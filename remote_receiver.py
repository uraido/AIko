# ------------ Imports ---------------

import socket

# ------------------------------------



# ------------ Set Up ----------------
  
# take the server name and port name
host = 'local host'
port = 5000
#server_ip = '26.124.79.180'  	# Ulaidh's ID (FOR RCHART TO USE)
server_ip = '26.246.74.120'		# Rchart's ID (FOR ULAIDH TO USE)

# ------------------------------------


while True:

	try:
		# create a socket at client side
		# using TCP / IP protocol
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		  
		# connect it to server and port
		# number on local computer.
		s.connect((server_ip, port))
		#s.connect(('127.0.0.1', port))

		# receive message string from
		# server, at a time 1024 B
		msg = s.recv(1024)

		message = msg.decode()[:-1]
		completion_option_selected = msg.decode()[-1]

		print(message)
		print(completion_option_selected)
		print()

		# disconnect the client
		s.close()
	except:
		pass