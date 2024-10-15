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
        # self.bh = BaslerHandler(config_path)
        pass

    def get(self, cam_id):

        # import ipdb
        # ipdb.set_trace()
        # cameras_info = self.bh.get_cameras_info()
        # print(data)
        # camera_info = cameras_info[cam_id]
        camera_data = {"dio": "merda"}
        return jsonify(camera_data)


class ImageInfo(Resource):
    def __init__(self):
        # self.bh = BaslerHandler(config_path)
        pass

    def get(self, cam_id):

        # import ipdb
        # ipdb.set_trace()
        # images_info = self.bh.get_images_info()
        # image_info = images_info[cam_id]
        image_info = {"dio": "cano"}
        return jsonify(image_info)


class Image(Resource):
    def __init__(self):
        # self.bh = BaslerHandler(config_path)
        pass

    # load an image and return it
    def get(self, cam_id):

        # self.bh.remove_images()
        # self.bh.capture(cam_ids=cam_id, exposure_time="auto")
        # image_path = str(next(images_path.glob("*.png")).resolve())
        image_path = "/home/manu/Desktop/download.png"

        request_img = send_file(
            image_path,
            mimetype="image/png",
        )
        return request_img

        # with open(image_path, "rb") as image_file:
        #     encoded_image = base64.b64encode(image_file.read()).decode("utf-8")
        # # return jsonify({"image": None, "data": {"hello": "world"}})
        # return jsonify({"image": encoded_image, "data": {"hello": "world"}})


api.add_resource(Image, "/camera/<int:cam_id>")
api.add_resource(ImageInfo, "/camera/<int:cam_id>/image_info")
api.add_resource(CameraInfo, "/camera/<int:cam_id>/camera_info")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
