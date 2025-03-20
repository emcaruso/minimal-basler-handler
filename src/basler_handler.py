from pypylon import pylon, genicam
from basler_utils import (
    set_autoexposure,
    set_exposure,
    set_fps,
    get_exposure,
    white_balancing,
    set_gamma,
    remove_autogain,
)
import shutil
import datetime
from collections import defaultdict
from copy import deepcopy
from prettytable import PrettyTable
import json
import cv2
import os
import itertools
from typing import Union, List, Dict, Tuple
from omegaconf import OmegaConf
import logging
from pathlib import Path
from image_basler import ImageBasler
from qrcode import QRCodeDetector
from constants import forbidden_chars_win


class BaslerHandler:

    def __init__(self, config_path: str) -> None:
        """
        Initialize the object with the given confg file

        Args:
            config_path: path to the config file (.yaml)
        """

        self._cfg = OmegaConf.load(config_path)  # load config file
        self._setup_logger()  # setup logger

        # log startin session
        self._log.info("Basler handler started")
        self._log.info(f"Configfile: {config_path}\n")

        # set pixel format
        self._converter = pylon.ImageFormatConverter()
        self._converter.OutputPixelFormat = pylon.PixelType_BGR8packed

        # load configured cams
        r = self._load_configured_cams()
        if r:
            self._log.info(
                "Configured cameras loaded\n"
                + self._devices_info_to_string(self._devices_info_configured)
            )
        else:
            self._log.info("No cameras configured yet, run configure_cameras() method")

        # qrcode detector
        self.qrcodes = QRCodeDetector(config_path)

        self._load_features()

    def __del__(self) -> None:
        """
        Close the camera array
        """
        try:
            self._cam_array.Close()
        except:
            {}
        self._log.info("Session ended\n")
        # del logger
        del self._log

    ########################################
    ############## PROTECTED ###############
    ########################################

    def _load_features(self):
        self._load_devices()
        if not Path(self._cfg.data.pfs_dir).exists():
            raise ValueError(f"Path {self.cfg.data.pfs_dir} does not exist")
        else:
            info = list(self._devices_info_configured.keys())
            for i, cam in enumerate(self._cam_array):
                device = self._devices[i]
                cam.Open()
                name_model = device.GetModelName()
                name_cam= info[i]
                path_cam = Path(self._cfg.data.pfs_dir) / f"{name_cam}.pfs"
                path_model = Path(self._cfg.data.pfs_dir) / f"{name_model}.pfs"
                if not path_model.exists():
                    self._log.warning(f"Feature file for camera model {name_model} not found, creating new one")
                    pylon.FeaturePersistence.Save(str(path_model), cam.GetNodeMap())
                if path_cam.exists():
                    self._log.info(f"Loading features for camera {i} ({name_cam})")
                    pylon.FeaturePersistence.Load(str(path_cam), cam.GetNodeMap(), True)
                else:
                    self._log.warning(f"Feature file for camera {name_cam} not found, loading from camera model")
                    pylon.FeaturePersistence.Load(str(path_model), cam.GetNodeMap(), True)
                    self._log.warning(f"Save features for camera {name_cam}")
                    pylon.FeaturePersistence.Save(str(path_cam), cam.GetNodeMap())
                cam.Close()

    def _devices_info_to_string(self, devices_info: dict) -> str:
        """
        From a dictionary containing the info of devices, it returns a table in string format
        Args:
            devices_info: dictionary containing the info of the available devices
            include_id: if True, the camera id will be included in the table
        """

        devices_info_copy = deepcopy(devices_info)

        if len(devices_info) == 0:
            return "No devices\n"

        # pretty table
        table = PrettyTable()
        field_names = [
            "Camera",
        ]
        first_key = next(iter(devices_info))
        field_names += list(devices_info[first_key].keys())
        table.field_names = field_names
        for key, val in devices_info_copy.items():
            row = [key]
            row.extend(val.values())
            table.add_row(row)

        return table.get_string() + "\n"

    def _get_devices_info(self) -> dict:
        """
        Get information about available devices

        Returns:
            infos: A dictionary containing the info of the available devices
        """

        # default dict of dictionaries
        # devices_info = defaultdict(lambda: defaultdict(dict))
        devices_info = {}

        for count, device in enumerate(self._devices):  # for each cam

            # camera name
            key = "camera_" + str(count)
            devices_info[key] = {}

            # insert devices_info defined in config into the dictionary
            for info_key in self._cfg.camera_info:
                info = None
                if getattr(device, "Is" + info_key + "Available")():
                    info = getattr(device, "Get" + info_key)()
                devices_info[key][info_key] = info
            devices_info[key]["cam_idx"] = count
            devices_info[key]["rotation"] = 0
            devices_info[key]["exposure_time"] = self._cfg.grab.exposure_time_default
            devices_info[key]["gamma"] = 0.5

        return devices_info

    def _setup_logger(self) -> None:
        """
        Sets the logger used to log Basler camera infos and errors
        """

        # set logger
        self._log = logging.getLogger(__name__)
        self._log.setLevel(logging.INFO)

        # Create a file handler
        file_dir = os.path.dirname(self._cfg.log.filename)
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)
        file_handler = logging.FileHandler(self._cfg.log.filename)
        file_handler.setLevel(logging.INFO)

        # Create a stream handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Create a logging format
        formatter = logging.Formatter(self._cfg.log.format)
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add the handlers to the logger
        self._log.addHandler(file_handler)
        self._log.addHandler(console_handler)

    def _load_devices(self) -> None:
        """
        Load camera devices
        """

        # load devices
        tlf = pylon.TlFactory.GetInstance()
        self._devices = tlf.EnumerateDevices(
            [
                pylon.DeviceInfo(),
            ]
        )

        self._n_devices = len(self._devices)

        # set camera array
        self._cam_array = pylon.InstantCameraArray(self._n_devices)
        for idx, cam in enumerate(self._cam_array):
            cam.Attach(tlf.CreateDevice(self._devices[idx]))
            cam.SetCameraContext(idx)

        # update device infos
        self._devices_info_current = self._get_devices_info()

    def _set_fps(self, camera: pylon.InstantCamera, fps: int) -> None:
        set_fps(camera, fps)

    def _set_exposure(self, camera: pylon.InstantCamera, exposure_time: int) -> None:
        """
        Set exposure time of a camera given its id

        Args:
            camera: camera object
            exposure_time: exposure time to set
                           can be an int, indicating the exposure time in microseconds to apply
                           if 'auto', auto exposure is used
                           if None, it is set to 'auto'


        """

        # set fixed exposure time
        if exposure_time == "auto":
            set_autoexposure(
                camera,
                self._cfg.grab.autoexposure.brightness_val,
                self._cfg.grab.timeout,
            )

        elif exposure_time == "default":
            pass

        elif exposure_time == "hdr":
            raise Excepton("HDR mode not implemented yet")

        else:
            set_exposure(camera, exposure_time)

        # camera.Close()
        # camera.Open()
        # camera.StartGrabbing(pylon.GrabStrategy_LatestImages)

    def _stop_cams(self) -> None:
        """
        Stop all cameras from grabbing images
        """

        self._cam_array.StopGrabbing()
        self._cam_array.Close()

    def _grab_basic(
        self,
        cam_iden: str,
        exposure_time: Union[int, str] = None,
        gamma: float = 0.5,
        log=True,
    ) -> dict:
        """
        Grab one image from a camera.

        Args:
            cam_iden: camera identifier related to the camera that has to grab the image
            exposure_time: exposure time used when acquiring images
                           can be an int, indicating the exposure time in microseconds to apply
                           if 'auto', auto exposure is used
                           if None, it is set to 'auto'

        Returns:
            result: a dictionary containing, the camera id, the exposure time, the grabbed image and the device info.
                    The dictionary also contains a 'success' key, if it's false, an error occurred, and its description
                    will be inserted in the 'error_msg' field.
        """

        # if needed set the default exposure time
        if exposure_time is None:
            exposure_time = "auto"

        # control on input types
        error_msg = None
        if self._n_devices_configured == 0:
            error_msg = "No cameras configured, run configure_cameras() method"
        if error_msg is None and not isinstance(cam_iden, str):
            error_msg = f"cam_iden must be a string"
        if error_msg is None and not isinstance(exposure_time, int):
            if not exposure_time in ["auto", "hdr", "default"]:
                error_msg = f"exposure time must be an int value, or 'auto' or 'default'"  # or 'hdr'"
        # control on input ranges
        if error_msg is None and not (cam_iden in self._devices_info_configured.keys()):

            error_msg = f"Cam ids must be between 0 and the number of devices ({self._n_devices_configured})"

        # control on cam_iden
        camera = self._get_cam_from_iden(cam_iden)
        if isinstance(camera, str):
            error_msg = camera
        elif not camera.IsOpen():
            camera.Open()  # open the camera

        # remove color correction
        white_balancing(camera, False)
        set_gamma(camera, gamma)
        remove_autogain(camera)

        if error_msg is not None:
            self._log.error(error_msg)
            return ImageBasler.init_error({}, error_msg)

        device_info = self._devices_info_configured[cam_iden]
        max_attempts = self._cfg.grab.max_attempts

        # init
        if not camera.IsGrabbing():
            # start the grabbing
            camera.StartGrabbing(pylon.GrabStrategy_LatestImages)

        # set exposure
        self._set_exposure(camera, exposure_time)  # set exposure time

        # grab loop
        n_attempts = 0
        while camera.IsGrabbing():

            # wait for an image and then retrieve it.
            grabResult = camera.RetrieveResult(
                self._cfg.grab.timeout, pylon.TimeoutHandling_ThrowException
            )

            # image grabbed successfully?
            if grabResult.GrabSucceeded():
                img = self._converter.Convert(grabResult).GetArray()
                grabResult.Release()

                # log
                if log:
                    self._log.info(
                        f"Grab successful: Cam: {cam_iden}, exposure_time: {str(exposure_time)}"
                    )
                break

            #  if max attempts is exceeded, exit
            elif n_attempts > max_attempts:
                self._log.error(error_msg)
                return ImageBasler.init_error({}, "Max number of attempts exceeded")

            # update number of attempts
            n_attempts += 1

        grabResult.Release()
        image_info = {
            "success": True,
            "cam_iden": cam_iden,
            "autoexposure": exposure_time == "auto",
        }
        image_info.update(device_info)
        image_info["exposure_time"] = get_exposure(camera)

        image_basler = ImageBasler(image_info, img)

        # apply rotation
        rotation_angle = device_info["rotation"]
        if "rotation" in device_info.keys():
            image_basler = image_basler.rotate_image(rotation_angle)
        #
        return image_basler

        # # Error handling
        # except genicam.GenericException as e:
        #     error_msg = f"An exception occurred: {e}"
        #     self._log.error(error_msg)
        #     return ImageBasler.init_error(device_info, error_msg)
        #

    def _load_configured_cams(self) -> bool:
        """
        Load the cameras that have been configured previously

        Returns:
            True if the cameras have been loaded successfully
            False otherwise
        """

        # load configured devices from json
        if os.path.exists(self._cfg.data.path_json):
            with open(self._cfg.data.path_json, "r") as f:
                self._devices_info_configured = json.load(f)

                # sort this dict of dicts by cam_idx attribute of dicts
                self._devices_info_configured = {
                    k: v
                    for k, v in sorted(
                        self._devices_info_configured.items(),
                        key=lambda item: item[1]["cam_idx"],
                    )
                }

                self._n_devices_configured = len(self._devices_info_configured)


            return True
        else:
            self._devices_info_configured = {}
            self._n_devices_configured = len(self._devices_info_configured)
            return False

    def _get_cam_from_iden(self, cam_iden: str) -> Union[pylon.InstantCamera, str]:
        """
        Get the camera object from the given id

        Returns:
            the camera object if it's available
            an error message otherwise
        """

        # control on input types
        err_msg = None
        if self._n_devices_configured == 0:
            err_msg = "No cameras configured yet, run configure_cameras() method"
        elif cam_iden.__class__ != str:
            err_msg = "cam_iden must be a string , not " + str(cam_iden.__class__)
        elif not cam_iden in self._devices_info_configured.keys():
            err_msg = f"The configured camera '{cam_iden}' is not available"

        if err_msg is not None:
            return err_msg

        # get configured infos
        cam_info = self._devices_info_configured[cam_iden]

        # find the match of info in the current devices
        for _, d in self._devices_info_current.items():
            if all([d[key] == cam_info[key] for key in self._cfg.match_keys]):
                return self._cam_array[d["cam_idx"]]

        return f"The configured camera '{cam_iden}' is not available"

    def _check_configured_cameras(self) -> Tuple[bool, str]:
        """
        Check if there are configured cameras

        Returns:
            a boolean indicating if there are configured cameras
        """

        # control on configured cameras
        if self._n_devices_configured == 0:
            err_msg = "No cameras configured yet, run configure_cameras() method"
            self._log.error(err_msg)
            return False
        else:
            return True

    def _grab_images_from_cams(
        self,
        number_of_images: int = 1,
        exposure_time: Union[int, List[int]] = None,
        gamma: float = 0.5,
        cam_idens: Union[str, List[str]] = None,
    ) -> List[Dict]:
        """
        Grab one or multiple images with one or more cameras

        Args:
            number_of_images: number of images that each camera must grab, 1 by default
            exposure_time: exposure time in microseconds used when acquiring images
                           can be an int, indicating the exposure time in microseconds to apply
                           can be a list of ints, indicating the exposure time for each image (length must match with number of images)
                           if 'auto', auto exposure is used
                           if None, it is set to 'auto'
            cam_idens: The camera identifiers related to the cameras we want to use to grab images
                     it can be a string, indicating a camera identifier
                     it can be a list of strings, indicating multiple cameras
                     if None, all available cameras will be involved

        Returns:
            results: The grab result, which is a list of dictionaries.
                     Each dictionary contains the grabbed image and other informations like
                     the camera id, the exposure time, the image number, the grabbed image and the device info.
                     the dictionary also contains a 'success' key, if it's false, an error occurred, and its description
                     will be inserted in the 'error_msg' field.
        """

        # log
        self._log.info("Grabbing images...")

        # load devices
        self._load_devices()

        # control on number of images
        error_msg = None
        if not isinstance(number_of_images, int):
            error_msg = f"number of images must be an int"
        elif number_of_images < 1 or number_of_images > self._cfg.grab.max_image_num:
            error_msg = f"number of images must be between 1 and max_image_num in the config file ({self._cfg.grab.max_image_num})"
        if error_msg is not None:
            self._log.error(error_msg)
            return error_msg

        # set exposure time, handle multiple exposure times
        if exposure_time.__class__ != list:
            exposure_time = list([exposure_time]) * number_of_images
        if len(exposure_time) != number_of_images:
            error_msg = f"Exposure time list has not same length {len(exposure_time)} of number of images ({number_of_images})"
            self._log.error(error_msg)
            return error_msg

        # set cam ids
        if cam_idens is None:
            cam_idens = list(self._devices_info_configured.keys())
        if cam_idens.__class__ != list:
            cam_idens = [cam_idens]

        # grab images
        results = []
        data = itertools.product(list(range(number_of_images)), cam_idens)
        timestamp = str(datetime.datetime.now())[:-7]
        for j, cam_iden in data:
            image_basler = self._grab_basic(cam_iden, exposure_time[j], gamma)
            image_basler.image_info = {
                "timestamp": timestamp,
                **image_basler.image_info,
            }
            results.append(image_basler)
        self._stop_cams()

        self._log.info("Grab completed\n")

        return results

    ########################################
    ################ PUBLIC ################
    ########################################

    def set_default_rotation(self, cam_iden: str, rotation_angle: int) -> dict:
        with open(self._cfg.data.path_json, "r") as f:
            data = json.load(f)
        if cam_iden not in data.keys():
            return {"error: ": f"Camera iden {cam_iden} not found"}
        if not isinstance(rotation_angle, int):
            return {
                "error: ": f"rotation_angle value must be an int",
            }
        if rotation_angle not in [0, 90, 180, 270]:
            return {
                "error: ": f"rotation_angle value must be 0, 90, 180 or 270",
            }
        data[cam_iden]["rotation"] = rotation_angle
        with open(self._cfg.data.path_json, "w") as f:
            json.dump(data, f, indent=4)
        return {}

    def set_default_exposure(self, cam_iden: str, exposure_time: int) -> dict:
        with open(self._cfg.data.path_json, "r") as f:
            data = json.load(f)

        if cam_iden not in data.keys():
            return {"error: ": f"Camera iden {cam_iden} not found"}

        if not isinstance(exposure_time, int) and exposure_time != "auto":
            return {
                "error: ": f"exposure_time value must be an int, or the string 'auto'",
            }

        data[cam_iden]["exposure_time"] = exposure_time

        with open(self._cfg.data.path_json, "w") as f:
            json.dump(data, f, indent=4)
        return {}

    def change_camera_iden(self, old_iden: str, new_iden: str) -> dict:
        if any([c in new_iden for c in forbidden_chars_win]):
            return {
                "error: ": f"Camera iden {new_iden} must NOT contain special characters: {forbidden_chars_win}"
            }

        with open(self._cfg.data.path_json, "r") as f:
            data = json.load(f)
        if old_iden not in data.keys():
            return {"error: ": f"Camera iden {old_iden} not found"}

        # substitute results
        img_info = self.get_all_img_info()
        if old_iden in img_info.keys():
            img_info[new_iden] = img_info.pop(old_iden)
            for d in img_info[new_iden]:
                d["cam_iden"] = new_iden
            with open(self._cfg.results.path_json, "w") as f:
                json.dump(img_info, f, indent=4)

        data[new_iden] = data.pop(old_iden)
        with open(self._cfg.data.path_json, "w") as f:
            json.dump(data, f, indent=4)
        return {}

    def remove_images(self) -> None:
        """
        Clear the results directory
        """
        shutil.rmtree(self._cfg.results.dir, ignore_errors=True)
        shutil.rmtree(self._cfg.results.path_json, ignore_errors=True)
        self._log.info("Captured images removed from disk\n")

    def configure_cameras(self) -> None:
        """
        Configure cameras with the settings defined in the config file
        It will also assign camera ids to cameras.

        Returns:
            True if the cameras have been configured successfully
            False otherwise
        """

        self._log.info("Configuring cameras...")

        self._load_configured_cams()
        devices_info_old = self._devices_info_configured

        # load devices
        self._load_devices()

        # new devices info
        devices_info_configured = self._devices_info_current

        # find matched devices with old configuration
        replace_dict = {}
        for k_old, d_old in devices_info_old.items():
            for k_new, d_new in devices_info_configured.items():
                if all([d_old[key] == d_new[key] for key in self._cfg.match_keys]):
                    replace_dict[k_new] = k_old

        for k_new, k_old in replace_dict.items():
            info_new = devices_info_configured.pop(k_new)
            new_dict = {}
            for k, v in info_new.items():
                if k in self._cfg.camera_info:
                    new_dict[k] = v
                else:
                    new_dict[k] = devices_info_old[k_old][k]
            devices_info_configured[k_old] = new_dict

        # save devices configured to the json file
        os.makedirs(os.path.dirname(self._cfg.data.path_json), exist_ok=True)
        with open(self._cfg.data.path_json, "w") as f:
            json.dump(devices_info_configured, f, indent=4)

        # load configured cams
        self._load_configured_cams()

        # log
        self.log_cameras()

        # clear stored results
        self.remove_images()

    def get_cameras_info(self) -> dict:
        return self._devices_info_configured

    def log_cameras(self) -> None:
        """
        Logs information of available devices, both configured cameras and current ones
        """

        # pretty table
        self._load_configured_cams()
        devices_info_configured = self._devices_info_configured

        # load new devices
        self._load_devices()
        devices_info_current = self._devices_info_current

        if list(devices_info_configured.values()) == list(
            devices_info_current.values()
        ):

            # log
            self._log.info(
                "Camera configuration:\n"
                + self._devices_info_to_string(devices_info_configured)
            )

        else:

            # # remove cam ids for clarity
            devices_info_copy = deepcopy(devices_info_current)
            # for key in devices_info_copy.keys():
            #     devices_info_copy[key].pop("cam_idx")
            #
            # log
            self._log.warning(
                "Devices changed from saved configuration!\n\n"
                + "Saved configuration:\n"
                + self._devices_info_to_string(devices_info_configured)
                + "\nDevices detected:\n"
                + self._devices_info_to_string(devices_info_copy)
                + "\nExecute configure_cameras() method to update the configuration\n"
            )

    def show_camera_stream(self, cam_iden: str, exposure_time: int = None) -> bool:
        """
        Displays a camera stream associated to camera related to its id.
        Ids are configured by running configure_cameras() method.
        Run log_cameras() to see the camera ids.
        Press 'q' to end the stream

        Args:
            cam_iden: The identifier of the camera
            Ids are configured by running configure_cameras() method.
            Run log_cameras() to see the camera ids.

        Returns:
            False or True wether an error occurred or not
        """

        # load devices
        self._load_devices()

        camera = self._get_cam_from_iden(cam_iden)

        # handle errors
        if isinstance(camera, str):
            self._log.error(camera)
            return False

        if not camera.IsOpen():
            camera.Open()  # open the camera
        # self._set_exposure(camera, exposure_time) # set exposure time
        if not camera.IsGrabbing():
            # start the grabbing
            camera.StartGrabbing(pylon.GrabStrategy_LatestImages)

        # set fps
        self._set_fps(camera, self._cfg.grab.fps)

        # streaming loop
        self._log.info(f"Image stream started (camera: {cam_iden})")
        image_name = f"Stream of camera: {cam_iden}"
        cv2.namedWindow(image_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(image_name, 800, 800)
        self._grab_basic(cam_iden, exposure_time, log=False)
        while True:
            image_basler = self._grab_basic(cam_iden, "default", log=False)

            # handle errors
            if image_basler.success() is False:
                self._log.error(image_basler.error_msg)
                break

            cv2.imshow(image_name, image_basler.image)
            key = cv2.waitKey(1)
            if key == ord("q"):
                self._stop_cams()
                cv2.destroyAllWindows()
                break
        self._log.info(f"Image stream ended (camera: {cam_iden})\n")

        return True

    def capture(
        self,
        number_of_images: int = 1,
        exposure_time: Union[int, List[int]] = None,
        gamma: float = 0.5,
        cam_idens: Union[str, List[str]] = None,
    ) -> List[ImageBasler]:
        """
        Grab one or multiple images with one or more cameras, and store them in the results directory

        Args:
            number_of_images: number of images that each camera must grab, 1 by default
            exposure_time: exposure time used when acquiring images
                           can be an int, indicating the exposure time in microseconds to apply
                           can be a list of ints, indicating the exposure time for each image (length must match with number of images)
                           if None, it is set to 'auto'
            cam_idens: The camera identifiers related to the cameras we want to use to grab images
                    it can be a string, indicating a camera identifier
                     it can be a list of strings, indicating multiple cameras
                     if None, all available cameras will be involved
                     Run log_cameras() to see the camera identifiers.

        Returns:
            results: The grab result, which is a list of ImageBasler objects.
                     Each dictionary contains the grabbed image and other informations like
                     the camera id, the exposure time, the image number, the grabbed image and the device info.
                     The dictionary also contains a 'success' key, if it's false, an error occurred, and its description
                     will be inserted in the 'error_msg' field.
        """

        if isinstance(cam_idens, str):
            cam_idens = [cam_idens]

        # grab
        results = self._grab_images_from_cams(
            number_of_images=number_of_images,
            exposure_time=exposure_time,
            cam_idens=cam_idens,
            gamma=gamma,
        )

        # save images in the results
        for i, image_basler in enumerate(results):
            cam_iden = cam_idens[i]
            image_basler.save(
                self._cfg.results.path_json, self._cfg.results.max_result_num
            )

        #     # resize result number
        #     data = json.load(f)
        #     if len(data[cam_iden]) > self._cfg.results.max_result_num:
        #         # remove exceeding images
        #         for d in data[cam_iden][: -self._cfg.results.max_result_num]:
        #             os.remove(d["image_path"])
        #
        #         # update data with resized results
        #         data[cam_iden] = data[cam_iden][-self._cfg.results.max_result_num :]
        # with open(self._cfg.results.path_json, "w") as f:
        #     json.dump(data, f, indent=4)
        #

    def get_all_img_info(self) -> dict:
        with open(self._cfg.results.path_json, "r") as f:
            data = json.load(f)
        return data

    def get_last_img_info(self, cam_iden: str) -> bool:
        """
        get info about all the collected images in the results directory
        """

        # load json file
        with open(self._cfg.results.path_json, "r") as f:
            data = json.load(f)

        if cam_iden not in data.keys():
            return {"error": f"No images with camera {cam_iden}"}

        return data[cam_iden][-1]

    # def log_images_info(self) -> bool:
    #     """
    #     log info about all the collected images in the results directory
    #     """
    #
    #     # get images data
    #     data = self.get_images_info()
    #
    #     # check if results are stored
    #     if not os.path.exists(self._cfg.results.path_json):
    #         self._log.info("No results stored yet\n")
    #         return False
    #
    #     # list of nested dicts to pretty table
    #     table = PrettyTable()
    #     for d in data:
    #         # initialize the table
    #         table.field_names = list(d.keys())
    #         table.add_row(list(d.values()))
    #     table = (
    #         "Results stored\n"
    #         + str(table)
    #         + f"\nTotal number of captured images: {len(data)}\n"
    #     )
    #
    #     # print the table
    #     self._log.info(table)
    #     return True

    def show_images(self) -> bool:
        """
        show images stored in the results directory
        """
        # check if results are stored
        if not os.path.exists(self._cfg.results.path_json):
            self._log.info("No results stored yet\n")
            return False
        # load json file
        with open(self._cfg.results.path_json, "r") as f:
            data = json.load(f)
        # show images
        for d in data:
            img_basler = ImageBasler.load(d)
            img_basler.show_img()
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        return True
