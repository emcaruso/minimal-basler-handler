from flask import Flask, send_file, jsonify
from flask_restful import Api, Resource, reqparse
from basler_handler import BaslerHandler
from pathlib import Path
import base64
import json

app = Flask(__name__)
api = Api(app)
script_path = Path(__file__).parent
data_path = script_path / ".." / "data" / "results"
images_path = data_path / "images"
config_path = script_path / ".." / "config.yaml"


class CameraInfo(Resource):
    def __init__(self):
        self.bh = BaslerHandler(config_path)
        # pass

    def get(self, cam_iden):
        cameras_info = self.bh.get_cameras_info()
        camera_info = cameras_info[cam_iden]
        # camera_info = {"hello": "world"}
        return jsonify(camera_info)


class ImageInfo(Resource):
    def __init__(self):
        self.bh = BaslerHandler(config_path)
        # pass

    def get(self, cam_iden):
        images_info = self.bh.get_images_info()
        image_info = images_info[0]
        # image_info = {"hello": "world"}
        return jsonify(image_info)


class Image(Resource):
    def __init__(self):
        self.bh = BaslerHandler(config_path)
        # pass

    # load an image and return it
    def get(self, cam_iden):

        print(cam_iden)
        self.bh.remove_images()
        self.bh.capture(cam_idens=cam_iden, exposure_time="auto")
        images_info = self.bh.get_images_info()
        image_path = images_info[0]["image_path"]
        # image_path = "/home/manu/Desktop/download.png"

        request_img = send_file(
            image_path,
            mimetype="image/png",
        )
        return request_img


# add resource at endpoint camera/string
api.add_resource(Image, "/camera/<string:cam_iden>")
api.add_resource(ImageInfo, "/camera/<string:cam_iden>/image_info")
api.add_resource(CameraInfo, "/camera/<string:cam_iden>/camera_info")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
