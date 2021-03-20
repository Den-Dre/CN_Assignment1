import os
import socket
from bs4 import BeautifulSoup as bs

# Initialising parameters
SERVER = '192.168.0.137'
PORT = 1234
ADDR = (SERVER, PORT)
FORMAT = 'utf-8'
HEADER = 100

# Initialise client
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Request command from user
HTTP_COMMAND, URI, PORT = input('Enter a request of the form: <HTTPCommand> <URI> <PORT>: ').split()
PORT = int(PORT)
# HTTP_COMMAND, URI, PORT = 'GET', 'www.google.com', 80


# Compose complete HTTP request
GET_request = f"{HTTP_COMMAND} / HTTP/1.1\r\nHost: {URI}\r\n\r\n"

# Connect to given URI
client.connect((URI, PORT))


def save_body(body):
    soup = bs(body, "html.parser")
    get_image_urls(soup)
    save_images(soup)
    with open(os.sep.join(['..', 'out', 'body.html']), 'w') as f:
        try:
            f.write(str(soup))
        except IOError:
            print("ERROR: couldn't write body to file")


def receive_length(length_to_receive, body_start):
    body = body_start + client.recv(max(length_to_receive, 0))
    save_body(body)


# TODO
def receive_chunks(start_of_body):
    body = start_of_body
    prev_resp = b""
    resp = client.recv(1024)
    while b"0\r\n\r\n" not in prev_resp + resp:
        prev_resp = resp
        resp = client.recv(1024)
        body += resp
    save_body(body)


def receive_body(prev_response=b""):
    response = prev_response + client.recv(2048)
    if b"Content-Length:" in response:
        for line in response.split(b'\r\n'):
            if b"Content-Length:" in line:
                total_length_body = int(line.split()[1])
                body_received = response.split(b"\r\n\r\n")[1]
                receive_length(total_length_body - len(body_received), body_received)
                return
        raise IOError("Expected Content-Length header.")
    elif b"Transfer-Encoding: chunked" in response:
        body_received = response.split(b"\r\n\r\n")[1]
        receive_chunks(body_received)
        return
    else:  # Header not yet completely processed
        receive_body(response)
        raise IOError("Header not completely processed.")


def get_image_urls(soup):
    img_urls = []
    for img in soup.find_all("img"):
        img_url = img.attrs.get("src")
        if img_url:
            img_urls.append(img_url)
    return img_urls
    # Based on: https://www.thepythoncode.com/article/download-web-page-images-python


# TODO
def save_images(soup):
    img_urls = get_image_urls(soup)
    for url in img_urls:
        print(url)
        if str(url).startswith('/'):
            request = f"GET {url} HTTP/1.1\nHost: {URI}\n\n"
        else:
            request = f"GET /{url} HTTP/1.1\nHost: {URI}\n\n"

        client.sendall(request.encode('ascii'))
        receive_image(url)
    change_src_to_local_img_location(soup)


def change_src_to_local_img_location(soup):
    for img in soup.find_all("img"):
        # Replace prefix of url of webpage with relative local path to directory of saved image:
        img['src'] = f"..{os.sep}img{os.sep}{img['src'].split('/')[-1]}"
        # if '/' not in img['src']:
        #     img['src'] = "../img/" + img['src']
        # else:
        #     img['src'] = img['src'].replace("/".join(img['src'].split('/')[:-1]), "../img/")
        #     # img['src'] = "/".join(os.getcwd().split("/")[:-1]) + '/' + img['src'].split("/")[-1]


def receive_img_length(total_length, body_start, name):
    body = body_start
    for i in range((total_length - len(body_start)) // 2048 + 1):
        body += client.recv(2048)
    # body = body_start + client.recv(length_to_receive)
    # headers = body.split(b'\r\n\r\n')[0]
    # image = body[len(headers) + 4:]
    # with open(f'{os.getcwd()}/img/{name.split("/")[-1]}', 'w+b') as f:
    with open(f'..{os.sep}img{os.sep}{name.split("/")[-1]}', 'w+b') as f:
        f.write(body)


# TODO
def receive_img_chunks(body_received, name):
    body = body_received
    prev_resp = b""
    resp = client.recv(1024)
    while b"0\r\n\r\n" not in prev_resp + resp:
        prev_resp = resp
        resp = client.recv(1024)
        body += resp
    with open(f'..{os.sep}img{os.sep}{name.split("/")[-1]}', 'w+b') as f:
        f.write(body)


def receive_image(name):
    prev_response = b""
    while True:
        response = prev_response + client.recv(2048)
        if b"Content-Length:" in response:
            for line in response.split(b'\r\n'):
                if b"Content-Length:" in line:
                    total_length_body = int(line.split()[1])
                    body_received = response.split(b"\r\n\r\n")[1]
                    print("Image length: ", total_length_body)
                    receive_img_length(total_length_body, body_received, name)
                    return
            raise IOError("Expected Content-Length header.")
        elif b"Transfer-Encoding: chunked" in response:
            body_received = response.split(b"\r\n\r\n")[1]
            receive_img_chunks(body_received, name)
            return
        else:  # Header not yet completely processed OR Error code
            prev_response = response
            # receive_image(name, response)
            # raise IOError(f"Header not completely processed, while processing {name}")
    # based on: https://stackoverflow.com/questions/43408325/how-to-download-image-from-http-server-python-sockets


def receive_header():
    # Average header size turns out to be approx. 700-800 bytes, up to 2kB.
    # source: https://stackoverflow.com/questions/5358109/what-is-the-average-size-of-an-http-request-response-header
    body = client.recv(2048)
    # HEAD contents shouldn't be stored in a file, as mentioned in th Q&A.
    # save_body(body)
    print('Resulting HEAD response:')
    print(body.decode('utf-8'))


def compose_request(request_type, rel_dir, contents):
    request = f"{request_type} {rel_dir} HTTP/1.1\r\n"
    request += f"Host: {URI}\r\n"
    request += f"Content-Length: {str(len(contents))}" + "\r\n\r\n"#"\r\n"
    request += contents + "\r\n"
    return request


def send_post():
    rel_dir = input('Relative directory to file: ')
    contents = input("String to POST to file on server: ")
    request = compose_request('POST', rel_dir, contents)
    client.sendall(request.encode('ascii'))


def send_put():
    rel_dir = input('Relative directory to file: ')
    contents = input('String to PUT to file on server: ')
    request = compose_request('PUT', rel_dir, contents)
    client.sendall(request.encode('ascii'))


if HTTP_COMMAND == 'GET':
    client.sendall(GET_request.encode('ascii'))
    receive_body()
elif HTTP_COMMAND == 'HEAD':
    client.sendall(GET_request.encode('ascii'))
    receive_header()
elif HTTP_COMMAND == 'POST':
    send_post()
elif HTTP_COMMAND == 'PUT':
    send_put()
# if HTTP_COMMAND in ["POST", "PUT"]:
#     text = input("String to send to HTTP server: ")
#     GET_request = f"{HTTP_COMMAND} / HTTP/1.1\r\nHost: {URI}\r\n" + text + "\r\n\r\n"
