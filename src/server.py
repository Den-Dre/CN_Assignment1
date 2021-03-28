import json
import os
import pathlib
import signal
import socket
import sys
import threading
import time
import mimetypes
import dateutil.parser as parser
from datetime import datetime

from dateutil.parser import parser
from markdown.util import deprecated


def get_ipv4():
    """ A method to retrieve the local IPv4-address of the machine.

    Works by connecting a socket to the DNS server of Google on port 80 and
    extracting the IPv4-address out of the the obtained name of the socket.
    Source: https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib
    """

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.connect(("8.8.8.8", 80))
    return sock.getsockname()[0]


def get_404_page():
    """ A that returns the HTML code for a 404 response.

    :return: The HTML code for a page that should be displayed on a 404 response.
    """

    return b"<!DOCTYPE html><html><body><p>Error 404: File not found.</p></body></html>"


def get_500_page():
    """ A that returns the HTML code for a 505 response.

    :return: The HTML code for a page that should be displayed on a 505 response.
    """

    return b"<!DOCTYPE html><html><body><p>Error 500: Server error.</p></body></html>"


def get_400_page():
    """ A that returns the HTML code for a 400 response.

    :return: The HTML code for a page that should be displayed on a 400 response.
    """

    return b"<!DOCTYPE html><html><body><p>Error 400: Bad request.</p></body></html>"


def get_modified_date(file_name):
    """
    Retrieve the Last-Modified date out of the lastModifiedDates.json
    file for the given file on this server

    Based on:
    https://stackoverflow.com/questions/237079/how-to-get-file-creation-modification-date-times-in-python

    :param file_name: The file of which the Last-Modified date is retrieved.
    :return: The Last-Modified date of the given file.
    """

    file_path = pathlib.Path('../myHTMLpage/' + file_name)
    modification_time = datetime.fromtimestamp(file_path.stat().st_mtime)
    return modification_time


def get_get_response_body(path):
    """ Get the body of the GET response of the file located at the parameter path

    :param path: The path to the file which is requested by the GET response.
    :return: Two values: the body of the requested file, and the HTTP status code.
    """

    if path == '/':
        path_to_read = os.sep.join(['..', 'myHTMLpage', 'myHTMLpage.html'])
    else:
        if path.startswith('/'):
            path = path[1:]
        path_to_read = os.sep.join(['..', 'myHTMLpage', path])
    try:
        with open(path_to_read, 'rb') as f:  # 'rb': read in binary mode
            file_type = mimetypes.guess_type(path_to_read)
            return f.read(), 200, file_type
    except IOError:
        return get_404_page(), 404, None


@deprecated
def update_last_modified(file_name, rel_dir):
    """Update the Last-Modified value of the given file in the lastModifiedDates.json file.

    :param file_name: The file to be updated.
    :param rel_dir: The relative directory where the file resides.
    """
    try:
        # Update Last-Modified date
        with open(os.path.join('..', 'myHTMLpage', 'lastModifiedDates'), 'r') as f:
            data = json.load(f)
            if file_name not in data.keys():
                data.update({file_name: ""})
            data[file_name] = datetime.now().replace(microsecond=0)
        with open(os.path.join('..', 'myHTMLpage', 'lastModifiedDates'), 'w') as f:
            f.write(json.dumps(data, indent=1, default=my_converter))
    except IOError:
        print("Couldn't write Last-Modified date for file: ", rel_dir)


def handle_post(data):
    """ Handle a POST-request: update Last-Modified date and append string to file.

    :param data: The POST-request.
    :return: Two values: the HTTP response code, and the appended string.
    """

    rel_dir = data.split()[1]
    string = data.split('\r\n\r\n')[1].rstrip()
    if rel_dir.startswith('/'):
        rel_dir = rel_dir[1:]

    # Update the Last-Modified field of the given file.
    # update_last_modified(file_name, rel_dir)

    try:
        # Append contents to file
        path_to_read = os.path.join('..', 'myHTMLpage', rel_dir)
        with open(path_to_read, 'a+') as f:
            try:
                f.write(string)
                file_type = mimetypes.guess_type(path_to_read)
                return 200, string, file_type
            except IOError:
                return 500, get_500_page()
    except IOError:
        print(f'ERROR: file at {rel_dir} not found.')
        return 404, get_404_page()


def handle_put(data):
    """ Handle a PUT-request: update the Last-Modified date and PUT the given string to a file.

    :param data: The PUT-request.
    :return: Two values: the HTTP status code and the string that was PUT.
    """
    rel_dir = data.split()[1]
    string = data.split('\r\n\r\n')[1].rstrip()
    if rel_dir.startswith('/'):
        rel_dir = rel_dir[1:]

    # Update the Last-Modified field of the given file.
    # update_last_modified(file_name, rel_dir)

    try:
        path_to_read = os.path.join('..', 'myHTMLpage', rel_dir)
        with open(path_to_read, 'w') as f:
            try:
                f.write(string)
                file_type = mimetypes.guess_type(path_to_read)
                return 200, string, file_type

            except IOError:
                return 500, get_500_page()
    except IOError:
        return 500, get_500_page()


def get_response_headers(code, body, file_type, file_name):
    """ Construct the headers of the HTTP response

    :param code: the HTTP response code the headers are based upon.
    :param body: The body of the HTTP response.
    :param file_type: The file type of the requested resource.
    :param file_name: The name of the requested file.
    :return: The HTTP response headers based on the given parameters
    """
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
    content_length = len(body)
    current_date = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())
    header += f'Date: {current_date}\r\n'
    header += f'Last-Modified: {get_modified_date(file_name)}\r\n'
    header += f'Content-Length: {content_length}\r\n'
    if file_type:
        header += f'Content-Type: {file_type[0]}; charset=UTF-8\r\n'
    return header + '\r\n'


def my_parse_date(text):
    """
    Parse a string representation of the
    Last-Modified date in into a datetime object.

    :param text: The string to be parsed
    :return: A UTC datetime representation of the given date as a datetime object.
    """

    date_format = "%a, %d %B %Y %H:%M:%S GMT"
    try:
        date = datetime.strptime(text, date_format)
    except ValueError:
        try:
            date = datetime.strptime(text, "%Y-%m-%d %H:%M:%S.%f").replace(microsecond=0)
        except ValueError:
            raise Exception('Couldn\'t parse If-Modified-Since date.')
    return date


@deprecated
def my_converter(o):
    """
    Convert a datetime object to a string to be
    able to write it to a JSON file. This method
    is passed as argument in a json.dumps call.

    Reference: https://code-maven.com/serialize-datetime-object-as-json-in-python

    :param o: The datetime object
    :return: A string representation of parameter o
    """
    if isinstance(o, datetime):
        return o.__str__()


def get_if_modified_since_date(request):
    """ Get the If-Modified-Since value of the given request.

    :param request: The request out of which the If-Modified-Since value should be extracted.
    :return: The If-Modified-Since value contained in this header.
    """
    for line in request.split('\r\n'):
        if "If-Modified-Since" in line:
            return my_parse_date(' '.join(line.split()[1:]))


def listen_to_client(client, address):
    """ Listen for HTTP requests of a client.

    partially based on:
    http://blog.wachowicz.eu/?p=256

    :param client: The client that will be listened to to receive its HTTP requests.
    :param address: The address of this client.
    """

    # Typical header sizes are 700-800 bytes, up to 2kB, ref:
    # https://dev.chromium.org/spdy/spdy-whitepaper
    size = 2048
    while True:
        try:
            data = client.recv(size)
            print('[RECEIVED DATA] ', data.decode('utf-8'))
            if data:
                request = data.decode('utf-8')
                request_type = request.split()[0]
                print("Detected ", request_type, " request.")

                path = request.split()[1]
                file_name = 'myHTMLpage.html' if path == '/' else path.split('/')[-1]

                if request_type in ['GET', 'HEAD']:
                    response_body, response_code, file_type = get_get_response_body(path)
                    if "Host:" not in request:
                        response_body = get_400_page()
                        response_code = 400
                    response_header = get_response_headers(response_code, response_body, file_type, file_name)

                    if "If-Modified-Since:" in request:
                        if get_modified_date(file_name) < get_if_modified_since_date(request):
                            client.sendall(get_response_headers(304, "", file_type, file_name).encode('ascii'))
                            break
                    if request_type == 'GET':
                        client.sendall(response_header.encode('ascii') + response_body)
                    elif request_type == 'HEAD':
                        client.sendall(response_header.encode('ascii'))
                elif request_type == 'POST':
                    response_code, string, file_type = handle_post(request)
                    response_header = get_response_headers(response_code, string, file_type, file_name)
                    client.sendall(response_header.encode('ascii'))
                    print(response_header)
                elif request_type == 'PUT':
                    response_code, string, file_type = handle_put(request)
                    response_header = get_response_headers(response_code, string, file_type, file_name)
                    client.sendall(response_header.encode('ascii'))
                    print(response_header)
            else:
                print("Client: ", address[0], " disconnected.")
                return
        except IOError:
            client.close()
            return


def graceful_shutdown(sig, dummy):
    """Handle a keyboard interrupt by successfully exiting the program.

    :param sig: The keyboard interrupt signal.
    :param dummy: A dummy variable to match the required signature.
    """

    sys.exit(1)


class ThreadedServer:
    """
    A class to represent a HTTP server with multi threading

    This is based on:
    https://stackoverflow.com/questions/23828264/how-to-make-a-simple-multithreaded-socket-server-in-python-that-remembers-client
    """

    def __init__(self, port):
        """
        Initialise this server with the given parameters.

        :param port: The port that this server will be hosted on.
        """

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
        """
        Listen to possible clients that send a connection request to this server.
        """

        # Max number of queued connections:
        self.sock.listen(5)
        while True:
            client, address = self.sock.accept()
            client.settimeout(3)
            threading.Thread(target=listen_to_client, args=(client, address)).start()
            print("[NEW CONNECTION] Connected to client: ", address[0])


if __name__ == "__main__":
    """
    Create an instance of a multithreaded server and listen to 
    possible connection requests of clients.
    """

    os.chdir(pathlib.Path(__file__).parent.absolute())
    # signal.signal(signal.SIGINT, graceful_shutdown)
    port_num = 1234
    s = ThreadedServer(port_num)
    s.listen()
