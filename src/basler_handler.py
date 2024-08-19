from pypylon import pylon, genicam
from basler_utils import set_autoexposure, set_exposure, set_fps
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

    def __del__(self) -> None:
        """
        Close the camera array
        """
        try:
            self._cam_array.Close()
        except:
            {}
        self._log.info("Session ended\n")

    ########################################
    ############## PROTECTED ###############
    ########################################

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
        field_names += list(devices_info["camera_0"].keys())
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
        devices_info = defaultdict(lambda: defaultdict(dict))

        for cam_id, device in enumerate(self._devices):  # for each cam

            # camera name
            key = "camera_" + str(cam_id)

            # insert devices_info defined in config into the dictionary
            for info_key in self._cfg.camera_info:
                info = None
                if getattr(device, "Is" + info_key + "Available")():
                    info = getattr(device, "Get" + info_key)()
                devices_info[key][info_key] = info
            devices_info[key]["cam_id"] = cam_id

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
            cam_id: id of the camera that has to grab images
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
                self._cfg.grab.autoexposure.brightness_thresh,
                self._cfg.grab.timeout,
            )

        elif exposure_time == "default":
            pass

        elif exposure_time == "hdr":
            raise Excepton("HDR mode not implemented yet")

        elif camera.ExposureTime.Value != exposure_time:
            set_exposure(camera, exposure_time)

        camera.Close()
        camera.Open()
        camera.StartGrabbing(pylon.GrabStrategy_UpcomingImage)

    def _stop_cams(self) -> None:
        """
        Stop all cameras from grabbing images
        """

        self._cam_array.StopGrabbing()
        self._cam_array.Close()

    def _grab_basic(
        self, cam_id: int, exposure_time: Union[int, str] = None, log=True
    ) -> dict:
        """
        Grab one image from a camera.

        Args:
            cam_id: camera id related to the camera that has to grab the image
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
        if error_msg is None and not isinstance(cam_id, int):
            error_msg = f"cam_id must be an int value"
        if error_msg is None and not isinstance(exposure_time, int):
            if not exposure_time in ["auto", "hdr", "default"]:
                error_msg = f"exposure time must be an int value, or 'auto' or 'default'"  # or 'hdr'"
        # control on input ranges
        if error_msg is None and not (
            cam_id >= 0 and cam_id < self._n_devices_configured
        ):
            error_msg = f"Cam ids must be between 0 and the number of devices ({self._n_devices_configured})"

        # control on cam_id
        camera = self._get_cam_from_id(cam_id)
        if isinstance(camera, str):
            error_msg = camera
        elif not camera.IsOpen():
            camera.Open()  # open the camera

        # control on exposure time range
        if (
            error_msg is None
            and isinstance(exposure_time, int)
            and not (
                exposure_time >= camera.ExposureTime.Min
                and exposure_time < camera.ExposureTime.Max
            )
        ):
            error_msg = f"Exposure time must be between the available range of the camera {camera.ExposureTime.Min} {camera.ExposureTime.Max}"

        # return error
        if error_msg is not None:
            self._log.error(error_msg)
            return ImageBasler.init_error({}, error_msg)

        device_info = self._devices_info_configured["camera_" + str(cam_id)]
        max_attempts = self._cfg.grab.max_attempts

        try:

            # init
            if not camera.IsGrabbing():
                # start the grabbing
                camera.StartGrabbing(pylon.GrabStrategy_UpcomingImage)
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
                    cam_id = grabResult.GetCameraContext()
                    img = self._converter.Convert(grabResult).GetArray()
                    grabResult.Release()

                    # log
                    if log:
                        self._log.info(
                            f"Grab successful: Cam: {str(cam_id)}, exposure_time: {str(exposure_time)}"
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
                "exposure_time": camera.ExposureTime.GetValue(),
                "autoexposure": exposure_time == "auto",
            }
            image_info.update(device_info)
            image_basler = ImageBasler(image_info, img)
            return image_basler

        # Error handling
        except genicam.GenericException as e:
            error_msg = f"An exception occurred: {e}"
            self._log.error(error_msg)
            return ImageBasler.init_error(device_info, error_msg)

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
                self._n_devices_configured = len(self._devices_info_configured)
            return True
        else:
            self._devices_info_configured = {}
            self._n_devices_configured = len(self._devices_info_configured)
            return False

    def _get_cam_from_id(self, cam_id: int) -> Union[pylon.InstantCamera, str]:
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
        elif cam_id.__class__ != int:
            err_msg = "cam_id must be an int value, not " + str(cam_id.__class__)
        elif cam_id >= self._n_devices_configured or cam_id < 0:
            err_msg = f"The configured camera {cam_id} is not available"

        if err_msg is not None:
            return err_msg

        # get configured infos
        cam_info = self._devices_info_configured["camera_" + str(cam_id)]

        # find the match of info in the current devices
        for _, d in self._devices_info_current.items():
            if all([d[key] == cam_info[key] for key in self._cfg.match_keys]):
                return self._cam_array[d["cam_id"]]

        return f"The configured camera {cam_id} is not available"

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
        cam_ids: Union[int, List[int]] = None,
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
            cam_ids: The camera ids related to the cameras we want to use to grab images
                     it can be an int, indicating a camera index
                     it can be a list of ints, indicating multiple cameras
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
        if cam_ids is None:
            cam_ids = list(range(self._n_devices_configured))
        if cam_ids.__class__ != list:
            cam_ids = [cam_ids]

        # grab images
        results = []
        data = itertools.product(list(range(number_of_images)), cam_ids)
        timestamp = str(datetime.datetime.now())[:-7]
        for j, cam_id in data:
            image_basler = self._grab_basic(cam_id, exposure_time[j])
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

        # load devices
        self._load_devices()

        # new devices info
        devices_info_configured = self._devices_info_current

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

    def log_cameras(self) -> None:
        """
        Logs information of available devices, both configured cameras and current ones
        """

        # pretty table
        devices_info_configured = self._devices_info_configured

        # load new devices
        self._load_devices()
        devices_info_current = self._devices_info_current

        if devices_info_configured == devices_info_current:

            # log
            self._log.info(
                "Camera configuration:\n"
                + self._devices_info_to_string(devices_info_configured)
            )

        else:

            # remove cam ids for clarity
            devices_info_copy = deepcopy(devices_info_current)
            for key in devices_info_copy.keys():
                devices_info_copy[key].pop("cam_id")

            # log
            self._log.warning(
                "Devices changed from saved configuration!\n\n"
                + "Saved configuration:\n"
                + self._devices_info_to_string(devices_info_configured)
                + "\nDevices detected:\n"
                + self._devices_info_to_string(devices_info_copy)
                + "\nExecute configure_cameras() method to update the configuration\n"
            )

    def show_camera_stream(self, cam_id: int, exposure_time: int = None) -> bool:
        """
        Displays a camera stream associated to camera related to its id.
        Ids are configured by running configure_cameras() method.
        Run log_cameras() to see the camera ids.
        Press 'q' to end the stream

        Args:
            cam_id: The id of the camera
            Ids are configured by running configure_cameras() method.
            Run log_cameras() to see the camera ids.

        Returns:
            False or True wether an error occurred or not
        """

        # load devices
        self._load_devices()

        camera = self._get_cam_from_id(cam_id)

        # handle errors
        if isinstance(camera, str):
            self._log.error(camera)
            return False

        if not camera.IsOpen():
            camera.Open()  # open the camera
        # self._set_exposure(camera, exposure_time) # set exposure time
        if not camera.IsGrabbing():
            # start the grabbing
            camera.StartGrabbing(pylon.GrabStrategy_UpcomingImage)

        # set fps
        self._set_fps(camera, self._cfg.grab.fps)

        # streaming loop
        self._log.info(f"Image stream started (camera: {str(cam_id)})")
        image_name = f"Stream of camera: {cam_id}"
        cv2.namedWindow(image_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(image_name, 800, 800)
        self._grab_basic(cam_id, exposure_time, log=False)
        while True:
            image_basler = self._grab_basic(cam_id, "default", log=False)

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
        self._log.info(f"Image stream ended (camera: {str(cam_id)})\n")

        return True

    def capture(
        self,
        number_of_images: int = 1,
        exposure_time: Union[int, List[int]] = None,
        cam_ids: Union[int, List[int]] = None,
        replace: bool = False,
    ) -> List[ImageBasler]:
        """
        Grab one or multiple images with one or more cameras, and store them in the results directory

        Args:
            number_of_images: number of images that each camera must grab, 1 by default
            exposure_time: exposure time used when acquiring images
                           can be an int, indicating the exposure time in microseconds to apply
                           can be a list of ints, indicating the exposure time for each image (length must match with number of images)
                           if None, it is set to 'auto'
            cam_ids: The camera ids related to the cameras we want to use to grab images
                     it can be an int, indicating a camera index
                     it can be a list of ints, indicating multiple cameras
                     if None, all available cameras will be involved
                     Ids are configured by running configure_cameras() method.
                     Run log_cameras() to see the camera ids.

        Returns:
            results: The grab result, which is a list of ImageBasler objects.
                     Each dictionary contains the grabbed image and other informations like
                     the camera id, the exposure time, the image number, the grabbed image and the device info.
                     The dictionary also contains a 'success' key, if it's false, an error occurred, and its description
                     will be inserted in the 'error_msg' field.
        """

        # replace old results
        if replace:
            self.remove_images()

        # grab
        results = self._grab_images_from_cams(number_of_images, exposure_time, cam_ids)

        # save images in the results
        for image_basler in results:
            image_basler.save()

        # load json file
        with open(self._cfg.results.path_json, "r") as f:
            data = json.load(f)

        # resize result number
        if len(data) > self._cfg.results.max_result_num:
            # remove exceeding images
            for d in data[: -self._cfg.results.max_result_num]:
                os.remove(d["image_path"])

            # uddate data with resized results
            data = data[-self._cfg.results.max_result_num :]
            with open(self._cfg.results.path_json, "w") as f:
                json.dump(data, f, indent=4)

    def log_images_info(self) -> bool:
        """
        log info about all the collected images in the results directory
        """

        # check if results are stored
        if not os.path.exists(self._cfg.results.path_json):
            self._log.info("No results stored yet\n")
            return False

        # load json file
        with open(self._cfg.results.path_json, "r") as f:
            data = json.load(f)

        # list of nested dicts to pretty table
        table = PrettyTable()
        for d in data:
            # initialize the table
            table.field_names = list(d.keys())
            table.add_row(list(d.values()))
        table = (
            "Results stored\n"
            + str(table)
            + f"\nTotal number of captured images: {len(data)}\n"
        )

        # print the table
        self._log.info(table)
        return True

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
