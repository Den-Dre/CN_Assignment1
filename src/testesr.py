# from PIL import Image
# import os
#
# string = '../img//googlelogo_white_background_color_272x92dp.png'
# path = '../img/' + string.split('/')[-1]
# with open(path, 'w+b') as f:
#     f.write()


from PIL import Image
import os

string = '../img//googlelogo_white_background_color_272x92dp.png'
path = '/img/' + string.split('/')[-1]
Image.open(f'{"/".join(os.getcwd().split("/")[:-1])}' + path).show()

path = 'thisisapath.test'
print(os.sep.join(['..', 'myHTMLpage', path]))
