import cv2
import os
import json
import numpy as np
from pathlib import Path

# from pyzbar.pyzbar import decode
import zxing
from omegaconf import OmegaConf


class QRCodeDetector:

    def __init__(self, config_path: str) -> None:
        self._cfg = OmegaConf.load(config_path)  # load config file

    # combine methods and returns the union of the lists
    def detect_qrcodes(self, image_path: str):
        res = []
        # res += self._detect_qrcodes_cv2(image_path)
        # res += self._detect_qrcodes_pyzbar(image_path)
        res += self._detect_qrcodes_zxing(image_path)
        return list(set(res))

    def _detect_qrcodes_zxing(self, image_path: str, res_old=[]):

        img = cv2.imread(image_path)

        tmp_path = str(Path(os.getcwd()) / "qrcode_tmp.png")

        # Initialize the ZXing Barcode Reader
        reader = zxing.BarCodeReader()
        # Decode the QR codes in the image
        res = reader.decode(image_path)

        if res.points != []:
            x_min = int(min([p[0] for p in res.points]))
            x_max = int(max([p[0] for p in res.points]))
            y_min = int(min([p[1] for p in res.points]))
            y_max = int(max([p[1] for p in res.points]))

            img[y_min:y_max, x_min:x_max, :] = 0
            # save image
            cv2.imwrite(tmp_path, img)
            res_new = self._detect_qrcodes_zxing(tmp_path, res_old + [res.parsed])
            return res_new
        else:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            return res_old

    def _detect_qrcodes_cv2(self, image_path: str):
        image = cv2.imread(image_path)
        # Initialize QRCode detector
        detector = cv2.QRCodeDetector()

        # Detect and decode the QR code
        retval, decoded_info, points, straight_qrcode = detector.detectAndDecodeMulti(
            image
        )

        # If points are detected, it means QR codes are found
        if points is not None:
            # Only return detected data (QR code content) that is non-empty
            return [d for d in decoded_info if d]
        else:
            # Return an empty list if no QR code is detected
            return []

    def _detect_qrcodes_pyzbar(self, image_path: str):

        image = cv2.imread(image_path)
        # Convert the image to grayscale (often improves detection rate)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Detect QR codes using pyzbar
        decoded_objects = decode(gray)

        # Extract decoded information from each detected QR code
        decoded_info = [obj.data.decode("utf-8") for obj in decoded_objects if obj.data]

        return decoded_info

    #
    def decode(self, image_path):

        # add qrcodes
        qr_list = self.detect_qrcodes(image_path)
        qr_data = {"qrcodes": qr_list}

        return qr_data


if __name__ == "__main__":
    qr = QRCodeDetector(
        config_path="/home/emcarus/Desktop/covisionlab/alpitronic_basler/config.yaml"
    )
    img_path = "/home/emcarus/Downloads/qrcodes.png"
    res = qr.detect_qrcodes(img_path)
    print(res)
