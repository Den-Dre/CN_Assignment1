import socket


def get_ipv4():
    s_temp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s_temp.connect(("8.8.8.8", 80))
    return s_temp.getsockname()[0]


HOST = get_ipv4()
PORT = 1234        # The port used by the server

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    while True:
        data = input("Data to send to server: ")
        if data == 'q':
            break
        s.sendall(data.encode('utf-8'))
        data = s.recv(1024)
        print('Received data: ', repr(data.decode('utf-8')))
