#  Minimal Basler Handler

### installation
Required packages are listed in the *requirements.txt* file
```
pip install -r requirements.txt
```
### How to run?

The file *basler_handler.py* contains a class *BaslerHandler* capable of interacting with connected Basler cameras. To instantiate an object of such class, a path to a .yaml config file (like *config.yaml*) must be passed to the constructor:
```
basler_handler = BaslerHandler( "path_to_config.yaml" )
```
The main methods are:

- **log_devices_info()**
Log and show on terminal informations about the available cameras connected. Logs are saved in the file specified in the config file.

- **show_camera_stream(cam_id, exposure_time)**
Display the image stream related to the camera represented by the camera id, which is an int value ( to know camera ids, look at the log coming from *log_devices_info()* ). The exposure time argument is the amount of time in microseconds for grabbing images. The *fps* value of the stream is the one reported in the config file. To exit from the stream visualization, press Q on the keyboard.

- **grab_images_from_cams( number_of_images, exposure_time, cam_ids)**
grab one or more images from one or more cams. By default, *number_of_images* is 1, *exposure_time* is the default value in the config file, *cam_ids* is None, meaning that all the available cameras will be used. The *exposure_time* argument (expressed in microseconds), can be also a list with the same length of *number_of_images*: i.e. each image will be grabbed with a different exposure time. Also *cam_ids* can be a list of different cam ids.
This function, returns the grab result as a list of dictionaries, where each dictionary is the outcome of a grab operation and it contains the camera id, the exposure time, the image number and some device info.  The dictionary also contains a 'success' key, if it's false an error occurred, and its description will be inserted in the 'error_msg' field.
\
Below some examples: 
\
All cameras, grab an image with the default exposure time value:\
```basler_handle.grab_images_from_cams()```
\
Cameras 0 and 3, grab an image with the default exposure time value:\
```basler_handle.grab_images_from_cams( cam_ids = [0, 3] )```
\
All cameras, grab two images with exposure times 10000 and 50000\
```basler_handle.grab_images_from_cams( number_of_images = 2, exposure_time = [10000, 50000] )```
\
Camera 2, grab five images with exposure time 10000\
```basler_handle.grab_images_from_cams( number_of_images = 5, exposure_time = 10000, cam_ids = 2 )```

- **show_results( results )**
This function is a simple visualizer of the outputs coming from the function *grab_images_from_cams*. It will display all the images contained in the results.

If the *basler_handler.py* file is executed, some methods of the class are called for qualitative tests.
