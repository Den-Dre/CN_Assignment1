import errno
import os
import select
import socket
from time import sleep

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

if HTTP_COMMAND in ["POST", "PUT"]:
    text = input("String to send to HTTP server: ")
    GET_request = f"{HTTP_COMMAND} / HTTP/1.1\r\nHost: {URI}\r\n" + text + "\r\n\r\n"

# Connect to given URI
client.connect((URI, PORT))

# HEAD request to find length of body
head_request = f"HEAD / HTTP/1.1\r\nHost: {URI}\r\n\r\n"
client.sendall(head_request.encode('ascii'))
result = client.recv(4096)
# result = b''
# while True:
#     try:
#         data = client.recv(1024, 0x40)
#         if data == b'':
#             print("Header reading complete.")
#             break
#         print(data)
#     except IOError:
#         print("Header reading complete.")
#         break
#     result += data
body_length = -1
chunked = False
if b"Content-Length:" in result:
    for line in result.split(b'\n'):
        if b"Content-Length:" in line:
            body_length = int(line.split()[1])
            print("Body length: ", body_length)
            chunked = False
            break
elif b"Transfer-Encoding: chunked" in result:
    chunked = True
else:
    chunked = False

# Bij HEAD www.tinyos.net krijgen we geen Content-Lenght, noch Chunked Encoding field.
# Dit betekent dat er Content-Length gebruikt wordt maar dit enkel in de GET response zijn header staat:
# https://stackoverflow.com/questions/27868314/avoiding-content-length-in-head-response


# Send GET request to retrieve body of response:
# sendall() instead of send to repeat send() until complete buffer has been sent:
# https://stackoverflow.com/questions/34252273/what-is-the-difference-between-socket-send-and-socket-sendall
client.sendall(GET_request.encode('ascii'))

# result = response = client.recv(4096)
# while b"</html>" not in response:
#     response = client.recv(4096)
#     result += response
# result = result.decode('utf-8')
# print(result)

# print("Fetching document body...")
# result = client.recv(1024)
# while select.select([client], [], [], 3)[0]:
#     data = client.recv(1024)
#     result += data
# print("Document body fetching completed.")

if not chunked:
    buffer_size = 1024
    nb_recvs = body_length // buffer_size

    print("Fetching document body...")
    result = client.recv(1024)
    for i in range(nb_recvs):
        data = client.recv(1024)
        result += data
    print("Document body fetching completed.")
    assert b"</html" in result
# else: TODO
#      header = b""
#     while True:
#         result = client.recv(1024)
#         for line in result.split(b"\r\n"):
#             header += line
#             if line.endswith(b"\r\n\r\n"):  # End of the header, start parsing chunks


# Alternative: using MSG_DONTWAIT recv()
# halt = False
# while True:
#     try:
#         data = client.recv(1024, 0x40)
#         print(data)
#     except IOError as e:
#         err = e.args[0]
#         if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
#             print("No more data available")
#             sleep(0.2)
#             if halt:
#                 break
#             halt = True
#         else:
#             # Now a "real" problematic error has occurred
#             print(e)
#             raise IOError('recv() returned an error')
#     else:
#         if len(data) == 0:
#             # We've received the complete response
#             break
#         else:
#             # we successfully received data
#             result += data
# Based on: https://stackoverflow.com/questions/16745409/what-does-pythons-socket-recv-return-for-non-blocking-sockets-if-no-data-is-r
# result = result.decode('utf-8')


# Extract the <html> ... </html> portion out of the result of the GET response.
# The <html> tag can have parameters: <html input=.. ... >, thus we need to parse on '<html'
# body = "<html" + result.partition("<html")[2].partition("</html>")[0] + " </html>"

result_headers = body = result.split(b"\r\n\r\n")[0]
if HTTP_COMMAND == 'GET':
    body = result[len(result_headers)+4:]
soup = bs(body, "html.parser")

# with open('./out/body.html', 'w') as body_file:
#     try:
#         body_file.write(body)
#     except IOError as e:
#         print("ERROR: couldn't write body to file")


def get_image_urls():
    img_urls = []
    for img in soup.find_all("img"):
        img_url = img.attrs.get("src")
        if img_url:
            img_urls.append(img_url)
    return img_urls
    # Based on: https://www.thepythoncode.com/article/download-web-page-images-python


def get_content_length(r):
    temp_string = str(r).partition("Content-Length: ")[2].split()[0]
    length = int(''.join(filter(lambda j: j.isdigit(), temp_string)))
    print("Length: ", length)
    return length


def receive_image(name):
    res = client.recv(1024)
    # length = get_content_length(res)  # TODO: use this?

    # while select.select([client], [], [], 3)[0]:
    print("Fetching image...")
    while True:
        try:
            received = client.recv(1024, 0x40)  # 0x40 = MSG_DONTWAIT: makes .recv() non-blocking
        except IOError:
            print('Image fetching completed.')
            break
        res += received  # Must be placed outside of try-block, but in while loop ofc!
    headers = res.split(b'\r\n\r\n')[0]
    image = res[len(headers) + 4:]
    with open(f'{os.getcwd()}/img/{name.split("/")[-1]}', 'w+b') as f:
        f.write(image)
    # based on: https://stackoverflow.com/questions/43408325/how-to-download-image-from-http-server-python-sockets


# def receive_image2():


# CASE 1: image is on same server
def save_images():
    img_urls = get_image_urls()
    for url in img_urls:
        print(url)
        request = f"GET {url} HTTP/1.1\nHost: {URI}\n\n"
        client.sendall(request.encode('ascii'))
        receive_image(url)


def change_src_to_local_img_location():
    for img in soup.find_all("img"):
        # Replace prefix of url of webpage with relative local path to directory of saved image:
        img['src'] = img['src'].replace("/".join(img['src'].split('/')[:-1]), "../img/")


def save_body():
    with open('../out/body.html', 'w') as f:
        try:
            f.write(str(soup))
        except IOError:
            print("ERROR: couldn't write body to file")


# TODO
if HTTP_COMMAND == "GET":
    save_images()
    change_src_to_local_img_location()
save_body()

# def send(msg):
#     encoded = msg.encode(FORMAT)
#     client.send(encoded)
#
#
# while True:
#     send(input('Enter a message to send to the server: '))
#     if bool(client.recv(HEADER).decode(FORMAT)) == False:
#         break
#


print('Client terminating. Server terminated connection to this client.')
