import cv2
import json
import numpy as np
from typing import Union, List, Dict, Tuple
from PIL import Image, ImageDraw, ImageFont
import os


class ImageBasler:

    results_dir = os.path.join(
        os.path.relpath(os.path.dirname(__file__)), "..", "data", "results"
    )

    def __init__(self, image_info: dict, image: np.array) -> None:
        self.image = image
        self.image_info = image_info

    @staticmethod
    def init_error(image_info: dict, error_msg: str):
        image_basler = ImageBasler(image_info, None)
        image_basler.image_info["error_msg"] = error_msg
        image_basler.image_info["success"] = False
        return image_basler

    @staticmethod
    def show_multiple(image_basler_list) -> None:
        if isinstance(image_basler_list, str):
            print("ERROR: " + image_basler_list)
        else:
            for image_basler in image_basler_list:
                image_basler.show_img()
            cv2.waitKey(0)
            cv2.destroyAllWindows()

    def show(self):
        self.show_img()
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    def show_img(self) -> None:
        if self.image_info["success"]:
            image_name = f"cam: {self.image_info['cam_iden']}, timestamp: {self.image_info['timestamp']}"
            cv2.namedWindow(image_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(image_name, 800, 800)
            cv2.imshow(image_name, self.image)
        # else:
        #     print(self.image_info["error_msg"])

    def info(self) -> None:
        pass

    def success(self) -> bool:
        return self.image_info["success"]

    def error_msg(self) -> str:
        return self.image_info["error_msg"]

    def image(self) -> np.ndarray:
        return self.image_info["image"]

    @staticmethod
    def load(data):
        """
        returns an IMageBasler object from a dictionary inside a json file
        """

        image = cv2.imread(data["image_path"])
        image_basler = ImageBasler(image_info=data, image=image)
        return image_basler

    def save(self) -> True:

        key_order = [
            "timestamp",
            # "exposure_time",
            "autoexposure",
            "image_path",
            "success",
            "error_msg",
        ]

        if not self.image_info["success"] == False:

            image_name = f"{self.image_info['timestamp'].replace(' ','_')};cam_{self.image_info['cam_iden']}"
            images_dir = os.path.join(self.results_dir, "images")

            os.makedirs(self.results_dir, exist_ok=True)
            os.makedirs(images_dir, exist_ok=True)

            # add image path to image info
            image_path = f"{images_dir}/{image_name}.png"
            self.image_info["image_path"] = image_path
            self.image_info["error_msg"] = None

            # save image
            cv2.imwrite(image_path, self.image)

        else:
            self.image_info["cam_iden"] = None
            # self.image_info["exposure_time"] = None
            # self.image_info["autoexposure"] = None
            self.image_info["image_path"] = None

        self.image_info = {k: self.image_info[k] for k in key_order}
        # create json if not exist
        os.makedirs(self.results_dir, exist_ok=True)
        json_path = f"{self.results_dir}/results.json"
        if not os.path.exists(json_path):
            with open(json_path, "w") as f:
                f.write("")

        # Load existing data
        with open(json_path, "r") as f:
            try:
                data = json.load(f)
            except (
                json.JSONDecodeError
            ):  # If the file is empty, set data to an empty list
                data = []

        # Append new data
        data.append(self.image_info)

        # Write data back to file
        with open(json_path, "w") as f:
            json.dump(data, f, indent=4)
