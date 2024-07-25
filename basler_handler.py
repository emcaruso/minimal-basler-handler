from pypylon import pylon, genicam
import os
import itertools
from typing import Union, List, Dict
import pprint
from omegaconf import OmegaConf
from pathlib import Path
import logging


class BaslerHandler:

    def __init__(self, config_path: str) -> None:
        """
        Initialize the object with the given confg file

        Args:
            config_path: path to the config file (.yaml)
        """

        self._cfg = OmegaConf.load(config_path)  # load config file
        self._setup_logger()  # setup logger

        # set pixel format
        self._converter = pylon.ImageFormatConverter()
        self._converter.OutputPixelFormat = pylon.PixelType_BGR8packed

        # log startin session
        self._log.info("Basler handler started")
        self._log.info(f"Configfile: {config_path}")

    ########################################
    ############## PROTECTED ###############
    ########################################

    def _setup_logger(self) -> None:
        """
        Sets the logger used to log Basler camera infos and errors
        """

        # set logger
        self._log = logging.getLogger(__name__)
        self._log.setLevel(logging.INFO)

        # Create a file handler
        file_dir = os.path.dirname(self._cfg.log.filename)
        if not os.path.exists(file_dir): os.makedirs(file_dir)
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
        self._devices = tlf.EnumerateDevices([pylon.DeviceInfo(),])
        self.n_devices = len(self._devices)

        # set camera array
        self._cam_array = pylon.InstantCameraArray(self.n_devices)
        for idx, cam in enumerate(self._cam_array):
            cam.Attach(tlf.CreateDevice(self._devices[idx]))
            cam.SetCameraContext(idx)

        # update device infos
        self._devices_info = self.get_devices_info()

    def _set_fps(self, cam_id: int, fps: int) -> None:
        """
        Set fps rate for the given camera represented by id

        Args:
            cam_id: id relative to the camera that has to grab images
            fps: fps rate to set
        """

        camera = self._cam_array[cam_id]
        period = int((1/fps)*1e6)
        camera.BslPeriodicSignalPeriod.Value = period
        camera.BslPeriodicSignalDelay.Value = 0
        camera.TriggerSelector.Value = "FrameStart"
        camera.TriggerMode.Value = "On"
        camera.TriggerSource.Value = "PeriodicSignal1"

    def _set_exposure(self, cam_id: int, exposure_time: int) -> None:
        """
        Set exposure time of a camera given its id

        Args:
            cam_id: id of the camera that has to grab images
            exposure_time: exposure time to set

        """

        camera = self._cam_array[cam_id]
        if camera.__class__ == pylon.InstantCameraArray:
            for cam in camera:
                if cam.ExposureTime.GetValue() != exposure_time:
                    cam.ExposureTime.SetValue(exposure_time)
        elif camera.__class__ == pylon.InstantCamera:
            if camera.ExposureTime.GetValue() != exposure_time:
                camera.ExposureTime.SetValue(exposure_time)

    def _stop_cams(self) -> None:
        """
        Stop all cameras from grabbing images
        """

        self._cam_array.StopGrabbing()
        self._cam_array.Close()

    def _grab_basic(self, cam_id: int, exposure_time: int = None, log=True) -> dict:
        """
        Grab one image from a camera.

        Args:
            cam_id: camera id related to the camera that has to grab the image
            exposure_time: exposure time used when acquiring images
                           if None, exposure time is set to its default value defined in the config file

        Returns:
            result: a dictionary containing, the camera id, the exposure time, the grabbed image and the device info.
                    The dictionary also contains a 'success' key, if it's false, an error occurred, and its description
                    will be inserted in the 'error_msg' field.
        """

        # if needed set the default exposure time
        if exposure_time is None:
            exposure_time = self._cfg.grab.exposure_time_default

        # control on input types
        error_msg = None
        if error_msg is None and not isinstance(cam_id, int):
            error_msg = f"cam_id must be an int value"
        if error_msg is None and not isinstance(exposure_time, int):
            error_msg = f"exposure time must be an int value"
        # control on input ranges
        if error_msg is None and not (cam_id >= 0 and cam_id < self.n_devices):
            error_msg = f"Cam ids must be between 0 and the number of devices ({self.n_devices})"
        if error_msg is None and not (exposure_time >= self._cfg.grab.exposure_range[0] and exposure_time < self._cfg.grab.exposure_range[1]):
            error_msg = f"Exposure time must be between the range specified in the config file"
        # return error
        if error_msg is not None:
            self._log.error(error_msg)
            return {"success": False, "error_msg": error_msg}

        # set camera and max attempts param
        camera = self._cam_array[cam_id]
        max_attempts = self._cfg.grab.max_attempts

        try:

            # init
            if not camera.IsOpen():
                camera.Open()  # open the camera
            self._set_exposure(cam_id, exposure_time)  # set exposure time
            if not camera.IsGrabbing():
                # start the grabbing
                camera.StartGrabbing(pylon.GrabStrategy_UpcomingImage)

            # grab loop
            n_attempts = 0
            while camera.IsGrabbing():

                # wait for an image and then retrieve it.
                grabResult = camera.RetrieveResult(
                    self._cfg.grab.timeout, pylon.TimeoutHandling_ThrowException)

                # image grabbed successfully?
                if grabResult.GrabSucceeded():
                    cam_id = grabResult.GetCameraContext()
                    img = self._converter.Convert(grabResult).GetArray()
                    grabResult.Release()

                    # log
                    if log:
                        self._log.info(
                            f"Grab successful: Cam: {str(cam_id)}, exposure_time: {str(exposure_time)}")
                    break

                #  if max attempts is exceeded, exit
                elif n_attempts > max_attempts:
                    self._log.error(error_msg)

                    return {"success": False, "error_msg": "Max number of attempts exceeded"}

                # update number of attempts
                n_attempts += 1

            # return result
            grabResult.Release()
            result = {"cam_id": cam_id, "exposure_time": exposure_time, "image": img,
                      "device_info": self._devices_info[cam_id], "success": True}
            return result

        # Error handling
        except genicam.GenericException as e:
            error_msg = f"An exception occurred: {e}"
            self._log.error(error_msg)
            return {"success": False, "error_msg": error_msg}

    ########################################
    ################ PUBLIC ################
    ########################################

    def get_devices_info(self) -> dict:
        """
        Get information about available devices

        Returns:
            infos: A dictionary containing the info of the available devices
        """

        infos = {}

        for cam_id, device in enumerate(self._devices):  # for each cam

            # camera name
            infos[cam_id] = {}

            # insert infos defined in config into the dictionary
            for info_key in self._cfg.camera_info:
                info = None
                if getattr(device, "Is"+info_key+"Available")():
                    info = getattr(device, "Get"+info_key)()
                infos[cam_id][info_key] = info
            infos[cam_id]["cam_id"] = cam_id

        return infos

    def log_devices_info(self) -> None:
        """
        Logs information of available devices
        """

        self._load_devices()
        infos = self.get_devices_info()
        data = pprint.PrettyPrinter(indent=2, sort_dicts=False).pformat(infos)
        self._log.info(f"Info of devices:\n{data}\n")

    def show_camera_stream(self, cam_id: int, exposure_time: int = None) -> bool:
        """
        Displays a camera stream associated to camera related to the given id.
        Press 'q' to end the stream

        Args:
            cam_id: The id of the camera

        Returns:
            False or True wether an error occurred or not
        """

        self._load_devices()
        if not (cam_id >= 0 and cam_id < self.n_devices):
            self._log.error(f"Cam ids must be between 0 and the number of devices ({self.n_devices})")
            return False

        camera = self._cam_array[cam_id]
        if not camera.IsOpen():
            camera.Open()  # open the camera
        # self._set_exposure(camera, exposure_time) # set exposure time
        if not camera.IsGrabbing():
            # start the grabbing
            camera.StartGrabbing(pylon.GrabStrategy_UpcomingImage)

        # set fps
        self._set_fps(cam_id, self._cfg.grab.fps)

        # streaming loop
        self._log.info(f"Image stream started (camera: {str(cam_id)})")
        while True:
            result = self._grab_basic(cam_id, exposure_time, log=False)
            cv2.imshow(f"Stream of camera: {cam_id}", result["image"])
            key = cv2.waitKey(1)
            if key == ord('q'):
                self._stop_cams()
                cv2.destroyAllWindows()
                break
        self._log.info(f"Image stream ended (camera: {str(cam_id)})")

        return True

    def grab_images_from_cams(self, number_of_images: int = 1, exposure_time: Union[int, List[int]] = None, cam_ids: Union[int, List[int]] = None) -> List[Dict]:
        """
        Grab one or multiple images with one or more cameras

        Args:
            number_of_images: number of images that each camera must grab, 1 by default
            exposure_time: exposure time in microseconds used when acquiring images
                           can be an int, indicating the exposure time to apply
                           can be a list of ints, indicating the exposure time for each image (length must match with number of images)
                           if None, it is set to default value in the config file
            cam_ids: the camera ids related to the cameras we want to use to grab images
                     it can be an int, indicating a camera index
                     it can be a list of ints, indicating multiple cameras
                     if None, all available cameras will be involved

        Returns:
            results: the grab result, which is a list of dictionaries.
                     Each dictionary contains the grabbed image and other informations like
                     the camera id, the exposure time, the image number, the grabbed image and the device info.
                     the dictionary also contains a 'success' key, if it's false, an error occurred, and its description
                     will be inserted in the 'error_msg' field.                  
        """

        # update devices
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
            exposure_time = list([exposure_time])*number_of_images
        if len(exposure_time) != number_of_images:
            error_msg = f"Exposure time list has not same length {len(exposure_time)} of number of images ({number_of_images})"
            self._log.error(error_msg)
            return error_msg

        # set cam ids
        if cam_ids is None:
            cam_ids = list(range(self.n_devices))
        if cam_ids.__class__ != list:
            cam_ids = [cam_ids]

        # grab images
        results = []
        data = itertools.product(list(range(number_of_images)), cam_ids)
        for j, cam_id in data:
            res = self._grab_basic(cam_id, exposure_time[j])
            if res["success"]:
                res["image_number"] = j
            results.append(res)
        self._stop_cams()

        return results

    @staticmethod
    def show_results(results: List[Dict]) -> bool:
        """
        Simple method to visualize images inside the result list
        Press any key to exit from the visualizaition

        Args:
            cam_id: The id of the camera
        """

        # handle failures on grab requests
        if results.__class__ == str:
            print(f"Error on the grab request: {results}")
            return False

        for res in results:

            # handle failures on image acquisitions
            if not res["success"]:
                print(f"Error when grabbing an image: {res['error_msg']}")
            # show the images
            else:
                cv2.imshow(
                    f"cam: {res['cam_id']}, i: {res['image_number']}", res["image"])
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        return True


if __name__ == "__main__":

    # test basler handler
    import cv2

    config_path: Path = Path(__file__).parent / "config.yaml"
    basl_handl = BaslerHandler(config_path)
    basl_handl.log_devices_info()

    # --------- Positive tests ---------

    # show camera stream
    basl_handl.show_camera_stream(cam_id=0)

    # test all cam, default exposure
    results = basl_handl.grab_images_from_cams()
    basl_handl.show_results(results)

    # test one cam, multi exposure
    results = basl_handl.grab_images_from_cams(
        cam_ids=0, number_of_images=3, exposure_time=[1000, 10000, 50000])
    basl_handl.show_results(results)

    # test some cams, multi exposure
    results = basl_handl.grab_images_from_cams(
        cam_ids=[0, 1], number_of_images=3, exposure_time=[1000, 10000, 50000])
    basl_handl.show_results(results)

    # test all cams, multi exposure
    results = basl_handl.grab_images_from_cams(
        number_of_images=3, exposure_time=[1000, 10000, 50000])
    basl_handl.show_results(results)

    # --------- Negative tests ---------

    # wrong types

    results = basl_handl.grab_images_from_cams(number_of_images="j")
    basl_handl.show_results(results)

    results = basl_handl.grab_images_from_cams(
        number_of_images=2, exposure_time=0.1)
    basl_handl.show_results(results)

    results = basl_handl.grab_images_from_cams(cam_ids=0.5)
    basl_handl.show_results(results)

    # wrong ranges

    results = basl_handl.grab_images_from_cams(cam_ids=1000)
    basl_handl.show_results(results)

    results = basl_handl.grab_images_from_cams(number_of_images=-2)
    basl_handl.show_results(results)

    results = basl_handl.grab_images_from_cams(exposure_time=0)
    basl_handl.show_results(results)
