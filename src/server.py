import socket

# Get local IPv4 address
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# TODO: understand this,
#  link: https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib
# 8.8.8.8 is Google haar DNS test server.
s.connect(("8.8.8.8", 80))
SERVER = s.getsockname()[0]
# SERVER = '192.168.0.137'  # TODO: make this work with socket library, so that ipv4 isn't hardcoded
s.close()

PORT = 1234


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Zodat programma meerdere keren hetzelfde adres kan gebruiken
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)


ADDR = (SERVER, PORT)
server.bind(ADDR)

HEADER = 64  # TODO: find correct maximum size over HTTP
FORMAT = 'utf-8'  # TODO: change this when images are received
DISCONNECT_MESSAGE = 'q'


def start():
    server.listen()
    while True:
        conn, addr = server.accept()
        print('[NEW CONNECTION]: ', addr[0], ' connected to server.')
        connected = True
        while connected:
            msg = conn.recv(HEADER).decode(FORMAT).rstrip()
            print('[MESSAGE]: ', msg)
            if msg == DISCONNECT_MESSAGE:
                connected = False
            conn.send(bytes(connected))
        print('[CLOSE CONNECTION]: ', addr[0], " disconnected.")
        conn.close()


print('[STARTING]: server is starting...')
start()


