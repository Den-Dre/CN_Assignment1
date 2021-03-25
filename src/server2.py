import json
import os
import signal
import socket
import sys
import threading
import time
from datetime import datetime

# TODO:
#  redirect if not https ✓
#  500 code only thrown when server crashes, not with bad request ✓
#  Arguments to program should be given when program's called, only body of PUT/POST request should be interactive ✓
#  Http:// moet er ook nog bij kunnen ✓
#  Redirects bij code 301 volgen ✓
#  Fix: afbeelding soms niet volledig geladen (Google logo) ✓
#  Fix: afbeeldingen met src='volledige http uri' kunnen niet laden ✓
#  If-Modified-Since header: Fix date format
#  recv()-calls met verschil van to receive lengte doen werken.


def get_ipv4():
    """ A method to retrieve the local IPv4-address of the machine.

    Works by connecting a socket to the DNS server of Google on port 80 and
    extracting the IPv4-address out of the the obtained name of the socket.
    """

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.connect(("8.8.8.8", 80))
    return sock.getsockname()[0]


def get_404_page():
    return b"<!DOCTYPE html><html><body><p>Error 404: File not found.</p></body></html>"


def get_500_page():
    return b"<!DOCTYPE html><html><body><p>Error 500: Server error.</p></body></html>"


def get_400_page():
    return b"<!DOCTYPE html><html><body><p>Error 400: Bad request.</p></body></html>"


def get_modified_date(file_name):
    pass


def get_get_response(path):
    if path == '/':
        path_to_read = os.sep.join(['..', 'myHTMLpage', 'myHTMLpage.html'])
    else:
        path_to_read = os.sep.join(['..', 'myHTMLpage', path])
    try:
        with open(path_to_read, 'rb') as f:  # 'rb': read in binary mode
            return f.read(), 200
    except IOError:
        return get_404_page(), 404


def handle_post(data):
    rel_dir = data.split()[1]
    file_name = rel_dir.split('/')[-1]
    string = data.split('\r\n\r\n')[1].rstrip()

    try:
        # Store Last-Modified date
        with open('..' + os.sep + 'myHTMLpage' + os.sep + 'lastModifiedDates') as f:
            data = json.load(f)
            data[file_name] = datetime.now().replace(microsecond=0).isoformat()
        with open('..' + os.sep + 'myHTMLpage' + os.sep + 'lastModifiedDates', 'w') as f:
            f.write(json.dumps(data, indent=4))
    except IOError:
        print("Couldn't write Last-Modified date for file: ", rel_dir)

    try:
        # Append contents to file
        with open('..' + os.sep + 'myHTMLpage' + rel_dir, 'a+') as f:
            f.write(string)
            return 200, string
    except IOError:
        print(f'ERROR: file at {rel_dir} not found.')
        return 404, get_404_page()


def handle_put(data):
    rel_dir = data.split()[1]
    string = data.split('\r\n\r\n')[1].rstrip()
    with open('..' + os.sep + 'myHTMLpage' + rel_dir, 'w') as f:
        try:
            f.write(string)
            return 200, string
        except IOError:
            return 500, get_500_page()


def get_response_headers(code, body):
    header = ''
    if code == 200:
        header += 'HTTP/1.1 200 OK\r\n'
    elif code == 404:
        header += 'HTTP/1.1 404 Not Found\r\n'
    elif code == 500:
        header += 'HTTP/1.1 500 Internal Server Error\r\n'
    elif code == 304:
        header += 'HTTP/1.1 304 Not Modified\r\n'
    else:
        raise NotImplemented(f'Error code {code} not implemented. Body: {body}')
    header += 'Content-Type: text/html; charset=UTF-8\r\n'
    current_date = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())
    header += 'Date: ' + current_date + '\r\n'
    content_length = len(body)
    # header += f'Last-Modified: {get_modified_date(date)}'
    header += f'Content-Length: {content_length}\r\n'
    return header + '\r\n'


def get_if_modified_since(request):
    for line in request.split('\r\n'):
        if "If-Modified-Since" in line:
            return line.split()[1:]


def listen_to_client(client, address):
    size = 2048  # Typical header sizes are 700-800 bytes, up to 2kB, ref:
    # https://dev.chromium.org/spdy/spdy-whitepaper
    while True:
        try:
            data = client.recv(size)
            print('[RECEIVED DATA] ', data.decode('utf-8'))
            if data:
                #  Handle HTTP requests accordingly, partially based on:
                #  http://blog.wachowicz.eu/?p=256
                request = data.decode('utf-8')
                request_type = request.split()[0]
                print("Detected ", request_type, " request.")

                path = request.split()[1]
                response_body, response_code = get_get_response(path)
                if "Host:" not in request:
                    response_body = get_400_page()
                    response_code = 400
                response_header = get_response_headers(response_code, response_body)

                if request_type == 'GET':
                    if "If-Modified-Since" in request:
                        if_modified_since_date = get_if_modified_since(request)
                        file_name = path.split('/')[-1]
                        if get_modified_date(file_name) < if_modified_since_date:
                            client.sendall(get_response_headers(304, ""))
                            return
                    client.sendall(response_header.encode('ascii') + response_body)
                elif request_type == 'HEAD':
                    client.sendall(response_header.encode('ascii'))
                elif request_type == 'POST':
                    response_code, string = handle_post(request)
                    response_header = get_response_headers(response_code, string)
                    client.sendall(response_header.encode('ascii'))
                    print(response_header)
                elif request_type == 'PUT':
                    response_code, string = handle_put(request)
                    response_header = get_response_headers(response_code, string)
                    client.sendall(response_header.encode('ascii'))
                    print(response_header)

            else:
                print("Client: ", address[0], " disconnected.")
                break
        except IOError:
            client.close()
            return False


def graceful_shutdown(sig, dummy):
    """Handle keyboard interrupt

    :param sig: The keyboard interrupt
    :param dummy: A dummy variable to match the required signature
    """
    sys.exit(1)


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
        host_location = (str(self.host) + ":" + str(self.port)).replace(" ", "")
        print("Hosting at: ", host_location)

    def listen(self):
        self.sock.listen(5)  # Max number of queued connections
        while True:
            client, address = self.sock.accept()
            client.settimeout(60)
            threading.Thread(target=listen_to_client, args=(client, address)).start()
            print("[NEW CONNECTION] Connected to client: ", address[0])


if __name__ == "__main__":
    signal.signal(signal.SIGINT, graceful_shutdown)
    port_num = 1234
    s = ThreadedServer(port_num)
    s.listen()
