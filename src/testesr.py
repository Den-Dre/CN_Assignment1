# from PIL import Image
# import os
#
# string = '../img//googlelogo_white_background_color_272x92dp.png'
# path = '../img/' + string.split('/')[-1]
# with open(path, 'w+b') as f:
#     f.write()
import glob
import os
#
# string = '../img//googlelogo_white_background_color_272x92dp.png'
# path = '/img/' + string.split('/')[-1]
# Image.open(f'{"/".join(os.getcwd().split("/")[:-1])}' + path).show()
#
# path = 'thisisapath.test'
# print(os.sep.join(['..', 'myHTMLpage', path]))

# trimmed_uri = "www.google.com/dit/is/een/test"
# print(trimmed_uri.split('/')[0], '/'.join(trimmed_uri.split('/')[1:]))
# site = trimmed_uri.split('/')[0]
# print(site, trimmed_uri[len(site)+1:])
import pathlib
from datetime import datetime


def parse_uri(uri):
    trimmed_uri = uri
    if 'http:' in uri:
        trimmed_uri = uri.split("http://")[1]
    elif 'https:' in uri:
        raise NotImplemented('Https is not supported.')
    base_uri = trimmed_uri.split('/')[0]
    rel_path = trimmed_uri[len(base_uri):]
    return base_uri, rel_path


# print(parse_uri('http://www.google.com/dit/is/een/test.png'))
# print(parse_uri('www.google.com'))
# print(os.getcwd()[:-4])
# print(os.path.join('a','b','c'))

print("2021-03-25T15:12:00" > datetime.now().replace(microsecond=0).isoformat())
