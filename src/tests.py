from basler_handler import BaslerHandler
from pathlib import Path

# test basler handler
config_path: Path = Path(__file__).parent / "config.yaml"
basl_handl = BaslerHandler(config_path)

# basl_handl.configure_cameras()
# basl_handl.log_devices_info()
#
# --------- Positive tests ---------

# show camera stream
basl_handl.show_camera_stream(cam_id=0)
basl_handl.show_camera_stream(cam_id=1)

# # test all cam, default exposure
# results = basl_handl.grab_images_from_cams()
# basl_handl.show_results(results)
#
# # test one cam, multi exposure
# results = basl_handl.grab_images_from_cams(
#     cam_ids=0, number_of_images=3, exposure_time=[1000, 10000, 50000]
# )
# basl_handl.show_results(results)
#
# # test some cams, multi exposure
# results = basl_handl.grab_images_from_cams(
#     cam_ids=[0, 1], number_of_images=3, exposure_time=[1000, 10000, 50000]
# )
# basl_handl.show_results(results)
#
# # test all cams, multi exposure
# results = basl_handl.grab_images_from_cams(
#     number_of_images=3, exposure_time=[1000, 10000, 50000]
# )
# basl_handl.show_results(results)

# --------- Negative tests ---------

# wrong types

results = basl_handl.grab_images_from_cams(number_of_images="j")
basl_handl.show_results(results)

results = basl_handl.grab_images_from_cams(number_of_images=2, exposure_time=0.1)
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
