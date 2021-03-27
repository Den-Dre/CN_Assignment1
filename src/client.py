import glob
import os
import pathlib
import socket
import sys
from datetime import datetime

from bs4 import BeautifulSoup as bs


def get_ipv4():
    """ A method to retrieve the local IPv4-address of the machine.

    Works by connecting a socket to the DNS server of Google on port 80 and
    extracting the IPv4-address out of the the obtained name of the socket.
    """

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]


def get_image_urls(soup):
    """Retrieve the src-attributes of all img-objects in the given soup html object

    Based on:
    https://www.thepythoncode.com/article/download-web-page-images-python
    """

    img_urls = []
    for img in soup.find_all("img"):
        img_url = img.attrs.get("src")
        if img_url:
            img_urls.append(img_url)

        # Also retrieve version of image to show when mouse hovers over it (e.g.: www.tcpipguide.com)
        img_low_url = img.attrs.get("lowsrc")
        if img_low_url:
            img_urls.append(img_low_url)
    return img_urls


def parse_uri(uri):
    """Handle different input forms of the user-input uri.

    :param uri: The uri to be parsed
    :return: the uri extracted from the input,
    along with the possible relative path of the requested file located on this uri.
    """

    trimmed_uri = uri
    if 'http:' in uri:
        trimmed_uri = uri.split("http://")[1]
    elif 'https:' in uri:
        raise NotImplemented('Https is not supported.')
    base_uri = trimmed_uri.split('/')[0]
    rel_path = trimmed_uri[len(base_uri):]
    if rel_path == '':
        rel_path = '/'
    return base_uri, rel_path


def handle_moved_permanently(response):
    """ Handle a "301 Moved permanently" redirect
    :param response: The "301 Moved permanently" response to be handled.
    """

    if b"https:" in response:
        print("Https redirects not supported.")
    elif b"http:" in response:
        soup = bs(response, "html.parser")
        for a in soup.find_all("a"):
            new_uri = a.attrs.get("href")
            new_client = MyClient('GET', new_uri, 80)
            new_client.handle_request()


def clear_directory():
    files = '../out/*'
    r = glob.glob(files)
    for i in r:
        os.remove(i)


class MyClient:
    """
    A class to represent a socket client that can execute certain
    HTTP-requests on provided uri's on a provided port.
    """

    def __init__(self, request_type, uri, port):
        """ Initialise this client with the given parameters.

        :param request_type: The type of HTTP-request to be performed
        :param uri: The URI to be connected to.
        :param port: The port to be connected to.
        """

        self.HOST = get_ipv4()
        self.PORT = int(port)
        self.REQUEST_TYPE = request_type
        self.URI, self.REL_PATH = parse_uri(uri)
        self.ADDR = (self.HOST, self.PORT)
        self.FORMAT = 'utf-8'
        self.HEADER = 100
        self.body = b""
        self.header = b""

        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Compose complete HTTP request
        # self.request = f"{self.REQUEST_TYPE} {self.REL_PATH} HTTP/1.1\r\nHost: {self.URI}\r\n\r\n"
        self.request = self.compose_request(self.REQUEST_TYPE, self.REL_PATH, "")

        # Connect to given URI
        self.client.connect((self.URI, self.PORT))

    def handle_request(self):
        """ Handle the given HTTP-request."""

        if self.REQUEST_TYPE == 'GET':
            clear_directory()
            self.client.sendall(self.request.encode('ascii'))
            self.receive_body()
            self.save_images()
        elif self.REQUEST_TYPE == 'HEAD':
            self.client.sendall(self.request.encode('ascii'))
            self.receive_header()
        elif self.REQUEST_TYPE == 'POST':
            self.send_post()
        elif self.REQUEST_TYPE == 'PUT':
            self.send_put()

    def save_body(self):
        """
        Save the body, fetch the images present on the site
        and modify the html code accordingly
        """

        with open(os.sep.join(['..', 'out', 'index.html']), 'w') as f:
            try:
                f.write(self.body.decode('ISO-8859-1'))
            except IOError:
                print("ERROR: couldn't write body to file")

    def receive_length(self, length_to_receive, body_start):
        """ Receive the body of the uri in the case of Content-Length encoding.

        :param length_to_receive: The remaining length of the body to be received
        :param body_start: The part of the body that has already been received.
        """

        self.body = body_start
        while length_to_receive > 0:
            part = self.client.recv(2048)
            self.body += part
            length_to_receive -= len(part)

        # Inefficient alternative: receive byte by byte:
        # for i in range(length_to_receive):
        #     self.body += self.client.recv(1)
        self.save_body()

    def receive_chunks(self, start_of_body):
        """ Receive the body of the uri in the case of Chunked encoding.

        :param start_of_body: The part of the body that has already been received.
        """

        self.body = start_of_body
        prev_resp = b""
        resp = self.client.recv(1024)
        while b"0\r\n\r\n" not in prev_resp + resp:
            prev_resp = resp
            resp = self.client.recv(1024)
            self.body += resp
        self.save_body()

    def receive_body(self):
        """ Receive the body part of the html code of the uri.

        This implementation is based on the researched assumption
        that the length of a GET-response header ranges from 700-
        800 bytes to 2kB.
        Source: https://dev.chromium.org/spdy/spdy-whitepaper
        """

        response = self.client.recv(2048)
        if b"301 Moved Permanently" in response:
            handle_moved_permanently(response)
        if b"Content-Length:" in response:
            for line in response.split(b'\r\n'):
                if b"Content-Length:" in line:
                    total_length_body = int(line.split()[1])
                    self.header, body_received = response.split(b"\r\n\r\n")
                    print(self.header.decode('utf-8') + "\r\n")
                    self.receive_length(total_length_body - len(body_received), body_received)
                    return
        elif b"Transfer-Encoding: chunked" in response:
            self.header, body_received = response.split(b"\r\n\r\n")
            print(self.header.decode('utf-8') + "\r\n")
            self.receive_chunks(body_received)
            return
        else:  # Header not yet completely processed
            raise IOError("Header not completely processed.")

    def save_images(self):
        """
        Iterate through all the img-objects in this HTML file
        and fetch each of them with a seperate GET-request.

        Finally, the src-attributes of this HTML file are
        modified to the local location of the fetched images.

        The results are written to index.html
        """

        # Read in saved body of GET request
        with open(os.sep.join(['..', 'out', 'index.html']), 'r') as f:
            body = f.read()

        soup = bs(body, 'html.parser')
        img_urls = get_image_urls(soup)
        for url in img_urls:
            print('Fetching image at: ', url)
            if 'www' in url and self.URI not in url:
                # Handle external images with separate GET-request
                image_client = MyClient('GET', url, 80)
                image_client.handle_request()
                continue
            elif str(url).startswith('/'):
                request = f"\r\nGET {url} HTTP/1.1\r\nHost: {self.URI}\r\n\r\n"
            else:
                request = f"\r\nGET /{url} HTTP/1.1\r\nHost: {self.URI}\r\n\r\n"
            self.client.sendall(request.encode('ascii'))
            self.receive_image(url)

            # Replace src attribute
            body = body.replace(url, os.sep.join(['..', 'out', url.split('/')[-1]]))

        # Write updated body
        with open(os.sep.join(['..', 'out', 'index.html']), 'w') as f:
            f.write(body)

    def receive_img_length(self, total_length, body_start, name):
        """Receive an an image whose length is specified with Content-Length encoding.

        :param total_length: The Content-Length value of this image.
        :param body_start: The part of this image that has already been received.
        :param name: The name that will be given to this image.
        """

        body = body_start
        length_to_receive = total_length - len(body_start)
        while length_to_receive > 0:
            part = self.client.recv(2048)
            body += part
            length_to_receive -= len(part)

        # Inefficient alternative: receive byte by byte:
        # for i in range(total_length - len(body_start)):
        #     body += self.client.recv(1)
        with open(f'..{os.sep}out{os.sep}{name.split("/")[-1]}', 'w+b') as f:
            f.write(body)

    def receive_img_chunks(self, body_received, name):
        """Receive an an image whose length is specified with Chunked encoding.

        :param body_received: The part of this image that has already been received.
        :param name: The name that will be given to this image.
        """

        body = body_received
        prev_resp = b""
        resp = self.client.recv(2048)
        while b"0\r\n\r\n" not in prev_resp + resp:
            prev_resp = resp
            resp = self.client.recv(2048)
            body += resp
        # with open(f'{os.getcwd()}{os.sep}out{os.sep}{name.split("/")[-1]}', 'w+b') as f:
        with open(os.sep.join(['..', 'out', f'{name.split("/")[-1]}']), 'w+b') as f:
            f.write(body)

    def receive_image(self, name):
        """ Receive an image using a GET-request

        :param name: The name that will be given to the fetched image.
        based on: https://stackoverflow.com/questions/43408325/how-to-download-image-from-http-server-python-sockets
        """
        while True:
            response = self.client.recv(2048)
            if b"Content-Length:" in response:
                for line in response.split(b'\r\n'):
                    if b"Content-Length:" in line:
                        total_length_body = int(line.split()[1])
                        body_received = response.split(b"\r\n\r\n")[1]
                        # print("Image length: ", total_length_body)
                        self.receive_img_length(total_length_body, body_received, name)
                        return
                raise IOError("Expected Content-Length header.")
            elif b"Transfer-Encoding: chunked" in response:
                body_received = response.split(b"\r\n\r\n")[1]
                self.receive_img_chunks(body_received, name)
                return
            else:  # Header not yet completely processed OR Error code
                print('Error: couldn\'t receive image: ', name)
                raise IOError(f"Header not completely processed, while processing {name}")

    def receive_header(self):
        """Receive the header of the given URI and print it to the terminal.

        Average header size turns out to be approx. 700-800 bytes, up to 2kB.
        source: https://dev.chromium.org/spdy/spdy-whitepaper
        """

        self.header = self.client.recv(2048)
        print('Resulting HEAD response:')
        print(self.header.decode('utf-8'))

    def compose_request(self, request_type, rel_dir, contents):
        """
        Compose a HTTP-request of the given request_type.

        :param request_type: The type of request to be composed.
        :param rel_dir: The relative directory to be placed in this request.
        :param contents: The contents for a PUT/POST-request to be sent.
        :return: The complete request.
        """

        request = f"{request_type} {rel_dir} HTTP/1.1\r\n"
        request += f"Host: {self.URI}\r\n"
        # request += f"If-Modified-Since: 2022-03-25T15:12:00\r\n"
        # request += "If-Modified-Since: " + str(datetime.now().strftime("%a, %d %B %Y %H:%M:%S GMT"))
        if request_type in ['POST', 'PUT']:
            request += f"Content-Length: {str(len(contents))}\r\n"
            request += "\r\n"
            request += contents + "\r\n"
        request += "\r\n"
        return request

    def send_post(self):
        """Send a POST request with the given contents. """

        contents = input("String to POST to file on server: ")
        request = self.compose_request('POST', self.REL_PATH, contents)
        self.client.sendall(request.encode('ascii'))
        self.header = self.client.recv(2048).decode('utf-8')
        print(self.header, '\n')

    def send_put(self):
        """Send a PUT request with the given contents. """

        contents = input('String to PUT to file on server: ')
        request = self.compose_request('PUT', self.REL_PATH, contents)
        self.client.sendall(request.encode('ascii'))
        self.header = self.client.recv(2048).decode('utf-8')
        print(self.header, '\n')


if __name__ == '__main__':
    """
    Set the working directory, create and run the client.
    """

    os.chdir(pathlib.Path(__file__).parent.absolute())
    try:
        client = MyClient(sys.argv[1], sys.argv[2], sys.argv[3])
    except IndexError:
        print('Please give input of the form: client.py <HTTP REQUEST TYPE> <URI> <PORT>.')
        sys.exit(0)
    client.handle_request()
