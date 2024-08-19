import cmd
from basler_handler import BaslerHandler
from pathlib import Path


def parse(text: str, cls) -> list[int]:
    try:
        return [cls(c) for c in text.split()]
    except:
        return None


def get_exposure_time(exposure_time: str) -> int:
    try:
        _exposure_time = parse(exposure_time, int)
        if _exposure_time is None:
            raise ValueERrror
        if not check_single_arg(_exposure_time):
            return None
        exposure_time = _exposure_time[0]
    except:
        exposure_time = exposure_time.replace(" ", "").lower()
        if not exposure_time in ["auto", "default"]:
            print(
                "Invalid argument, exposure time time must be in ['auto','default'] or an int"
            )
            return None
    return exposure_time


def check_single_arg(arg: list[int]) -> bool:
    if len(arg) == 0:
        print("Please, provide at least one argument")
        return False
    if len(arg) > 1:
        print("Multiple arguments are not allowed, please provide only one argument")
        return False
    return True


class CameraCLI(cmd.Cmd):
    intro = "Welcome to camera cli, type 'help' or '?' for available commands"
    prompt = "camera >> "

    def __init__(self):
        super().__init__()

        # initialize basler handler
        config_path: Path = Path(__file__).parent.parent / "config.yaml"
        self.bh = BaslerHandler(config_path)

    # camera commands

    def do_list_cameras(self, _):
        "List configured cameras"
        self.bh.log_cameras()

    def do_configure_cameras(self, _):
        "Make and store a new camera configuration"
        self.bh.configure_cameras()

    # stream commands

    def do_show_camera_stream(self, arg):
        """
        Show camera stream

        Args:
            camera id: int, the id of the camera to show
        """

        # argument check
        cam_id = parse(arg, int)
        if cam_id is None:
            print("Invalid argument, put a single camera id")
            return False
        if not check_single_arg(cam_id):
            return False

        # show camera stream
        self.bh.show_camera_stream(cam_id[0])

    # capture commands

    def do_capture(self, arg) -> bool:
        """
        Send a capture command to the cameras, and save the images to disk

        Args:
            camera ids: int, the ids of the cameras to capture images from
            exposure time: int, the exposure time for the cameras, in microseconds
                           if set to 'auto', the cameras will use auto exposure
        camera ids and exposure time have to be separated by a comma

        Examples:
            'capture 0 2, 10000': captures an image on camera 0 and 2, with an exposure time of 10000
            'capture 1, auto': captures an image on camera 1, using auto exposure
            'capture': without arguments, camera ids and exposure time will be prompted intearctively
        """

        if arg == "":
            # get cam ids interactively
            print("Enter cam ids:")
            cam_ids = input()
            cam_ids = parse(cam_ids, int)
            if cam_ids is None:
                print("Invalid argument, put a sequence of camera ids")
                return False

            # get exposure time interactively
            print("Enter exposure time:")
            exposure_time = input()
            exposure_time = get_exposure_time(exposure_time)
            if exposure_time is None:
                return False

        else:
            # argument check
            try:
                cam_ids, exposure_time = arg.split(",")
            except:
                print(
                    "Invalid argument, put a sequence of camera ids and an exposure time value, separated by a comma"
                )
                return False
            cam_ids = parse(cam_ids, int)
            exposure_time = get_exposure_time(exposure_time)
            if exposure_time is None:
                return False

        # capture
        self.bh.capture(cam_ids=cam_ids, exposure_time=exposure_time)

    def do_list_images_info(self, _):
        "List info on captured images"
        self.bh.log_images_info()

    def do_show_images(self, _):
        "Show captured images"
        self.bh.show_images()

    def do_remove_images(self, _):
        "Remove captured images from disk"
        self.bh.remove_images()

    # exit command

    def do_exit(self, _):
        "Quit CLI"
        del self.bh
        return True


if __name__ == "__main__":
    CameraCLI().cmdloop()
