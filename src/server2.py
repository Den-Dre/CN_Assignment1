import socket
import threading
import time


def get_ipv4():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]


def ask_port():
    while True:
        port_tmp = input("Which port do you want to host on? ")
        try:
            return int(port_tmp)
        except ValueError:
            print("Please enter an integer value: ")
            pass


def get_404_page():
    return b"<!DOCTYPE html><html><body><p>Error 404: File not found</p></body></html>"


def get_get_response(path, request_type):
    if path == '/':
        path_to_read = '../myHTMLpage/myHTMLpage.html'
    else:
        path_to_read = '../myHTMLpage/' + path
    try:
        with open(path_to_read, 'rb') as f:  # 'rb': read in binary mode
            return f.read(), 200
    except IOError:
        if request_type in ['GET', 'HEAD']:
            print('ERROR: requested file not found.')
        return get_404_page(), 404


def handle_put(data):
    rel_dir = data.split()[1]
    string = data.split('\r\n\r\n')[1].rstrip()
    try:
        with open('../myHTMLpage' + rel_dir, 'a+') as f:
            f.write(string)
            return 200, string
    except IOError:
        return 400, get_404_page()


def get_response_headers(code, body):
    header = ''
    if code == 200:
        header += 'HTTP/1.1 200 OK\r\n'
    elif code == 404:
        header += 'HTTP/1.1 404 Not Found\r\n'
    header += 'Content-Type: text/html; charset=UTF-8\r\n'
    current_date = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())
    header += 'Date: ' + current_date + '\r\n'
    content_length = len(body)
    header += f'Content-Length: {content_length}\r\n'
    return header + '\r\n'


def listen_to_client(client, address):
    size = 2048  # Typical header sizes are 700-800 bytes, up to 2kB, ref:
    # https://stackoverflow.com/questions/5358109/what-is-the-average-size-of-an-http-request-response-header
    while True:
        try:
            data = client.recv(size)
            print('[RECEIVED DATA] ', data.decode('utf-8'))
            if data:
                #  Handle HTTP requests accordingly, partially based on:
                #  http://blog.wachowicz.eu/?p=256
                request = data.decode('utf-8')  # TODO: change decoding for images with PUT / POST request?
                request_type = request.split()[0]
                print("Detected ", request_type, " request.")

                path = request.split()[1]
                response_body, response_code = get_get_response(path, request_type)
                response_header = get_response_headers(response_code, response_body)
                if request_type == 'GET':
                    client.sendall(response_header.encode('ascii') + response_body)
                elif request_type == 'HEAD':
                    client.sendall(response_header.encode('ascii'))
                elif request_type == 'POST':
                    response_code, string = handle_put(request)
                    response_header = get_response_headers(response_code, string)
                    client.sendall(response_header.encode('ascii'))
                    print(response_header)
                elif request_type == 'PUT':
                    raise NotImplemented('Not implemented yet.')
            else:
                # raise Exception('Client disconnected')
                print("Client: ", address[0], " disconnected.")
                break
        except IOError:
            client.close()
            return False


# This is based on:
# https://stackoverflow.com/questions/23828264/how-to-make-a-simple-multithreaded-socket-server-in-python-that-remembers-client
class ThreadedServer:
    def __init__(self, port):
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = get_ipv4()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.sock.bind((self.host, self.port))
        except PermissionError:
            print("Please enter a port number larger than 1024.")
            exit()
        print("Hosting at: ", self.host, ":", self.port)

    def listen(self):
        self.sock.listen(5)  # Max number of queued connections
        while True:
            client, address = self.sock.accept()
            # client.settimeout(60)
            threading.Thread(target=listen_to_client, args=(client, address)).start()
            print("[NEW CONNECTION] Connected to client: ", address[0])


if __name__ == "__main__":
    # port_num = ask_port()
    port_num = 1234
    ThreadedServer(port_num).listen()
