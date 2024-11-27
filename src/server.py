from flask import Flask, send_file, jsonify
from flask_restful import Api, Resource, reqparse
from basler_handler import BaslerHandler
from pathlib import Path
import os
import base64
import json

app = Flask(__name__)
api = Api(app)
script_path = Path(__file__).parent
data_path = script_path / ".." / "data" / "results"
images_path = data_path / "images"
config_path = script_path / ".." / "config.yaml"

bh = BaslerHandler(os.path.realpath(str(config_path)))


def check_cam_iden(cam_iden):
    if cam_iden not in bh._devices_info_configured.keys():
        return False
    return True


class CameraInfo(Resource):

    def get(self, cam_iden):
        if not check_cam_iden(cam_iden):
            return jsonify({"error": f"Camera {cam_iden} not configured"})
        cameras_info = bh.get_cameras_info()
        camera_info = cameras_info[cam_iden]
        return jsonify({cam_iden: camera_info})


class ImageInfo(Resource):

    def get(self, cam_iden):
        if not check_cam_iden(cam_iden):
            return jsonify({"error": f"Camera {cam_iden} not configured"})
        image_info = bh.get_last_img_info(cam_iden)
        return jsonify(image_info)


class Image(Resource):

    # load an image and return it
    def get(self, cam_iden):
        if not check_cam_iden(cam_iden):
            return jsonify({"error": f"Camera {cam_iden} not configured"})

        devices_info = bh._devices_info_configured
        bh.capture(
            cam_idens=cam_iden, exposure_time=devices_info[cam_iden]["exposure_time"]
        )
        # bh._log.info("Reading QR codes")
        # bh.qrcodes.postprocess()
        images_info = bh.get_last_img_info(cam_iden)

        # if image_path is not None (no error):
        if images_info["success"]:
            image_path = images_info["image_path"]
            request_img = send_file(
                image_path,
                mimetype="image/png",
            )
            return request_img
        else:
            return jsonify(images_info)


class QRCode(Resource):
    def get(self, cam_iden):
        image_info = bh.get_last_img_info(cam_iden)
        image_path = image_info["image_path"]
        qr_data = bh.qrcodes.decode(image_path)
        return jsonify(qr_data)


class ListCameras(Resource):

    def get(self):
        bh._load_configured_cams()
        devices_info = bh._devices_info_configured
        return jsonify(devices_info)


class ConfigureCameras(Resource):

    def get(self):
        bh.configure_cameras()
        devices_info = bh._devices_info_configured
        return jsonify(devices_info)


class SetExposure(Resource):
    def get(self, cam_iden, exposure_time):
        if not check_cam_iden(cam_iden):
            return jsonify({"error": f"Camera {cam_iden} not configured"})
        try:
            exposure_time = int(exposure_time)
        except:
            {}
        res = bh.set_default_exposure(cam_iden, exposure_time)
        if res == {}:
            bh._load_configured_cams()
            devices_info = bh._devices_info_configured
            return jsonify(devices_info[cam_iden])
        else:
            print(res)
            return res


class SetRotation(Resource):
    def get(self, cam_iden, rotation):
        if not check_cam_iden(cam_iden):
            return jsonify({"error": f"Camera {cam_iden} not configured"})
        try:
            rotation = int(rotation)
        except:
            {}
        res = bh.set_default_rotation(cam_iden, rotation)
        if res == {}:
            bh._load_configured_cams()
            devices_info = bh._devices_info_configured
            return jsonify(devices_info[cam_iden])
        else:
            print(res)
            return res


class ChangeIdentifier(Resource):
    def get(self, cam_iden, new_iden):
        if not check_cam_iden(cam_iden):
            return jsonify({"error": f"Camera {cam_iden} not configured"})
        res = bh.change_camera_iden(cam_iden, new_iden)
        if res == {}:
            bh._load_configured_cams()
            devices_info = bh._devices_info_configured
            return jsonify(devices_info)
        else:
            print(res)
            return res


# add resource at endpoint camera/string
api.add_resource(Image, "/camera/<string:cam_iden>")
api.add_resource(ImageInfo, "/camera/<string:cam_iden>/image_info")
api.add_resource(CameraInfo, "/camera/<string:cam_iden>/camera_info")
api.add_resource(ListCameras, "/list_cameras")
api.add_resource(ConfigureCameras, "/configure_cameras")
api.add_resource(SetExposure, "/set_exposure/<string:cam_iden>/<string:exposure_time>")
api.add_resource(SetRotation, "/set_rotation/<string:cam_iden>/<string:rotation>")
api.add_resource(ChangeIdentifier, "/change_iden/<string:cam_iden>/<string:new_iden>")
api.add_resource(QRCode, "/camera/<string:cam_iden>/qrcodes")

if __name__ == "__main__":

    # debug mode
    app.run(host="0.0.0.0", port=80, debug=True)
    # app.run(host="0.0.0.0", port=5000, debug=True)

    # normal mode
    # app.run(host="0.0.0.0", port=80)
    # app.run(host="0.0.0.0", port=5000)

    # from waitress import serve
    # serve(app, host="0.0.0.0", port=80)
    # serve(app, host="0.0.0.0", port=5000)
