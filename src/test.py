import requests
import base64
from io import BytesIO
from PIL import Image


BASE = "http://127.0.0.1:5000/"

# import ipdb
#
# ipdb.set_trace()
response = requests.get(BASE + "camera/0")

# # Carica l'immagine se la richiesta è andata a buon fine
if response.status_code == 200:
    data = response.json()

    # dictionary data
    dictionary_data = data["data"]
    print(dictionary_data)

    # image
    if data["image"] is None:
        print("No image data")
    else:
        image_data = base64.b64decode(data["image"])
        image = Image.open(BytesIO(image_data))
        image.show()  # Or save to disk using image.save()
