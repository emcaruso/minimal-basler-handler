#  Minimal Basler Handler

A simple library to interact with Basler Cameras. It provides image capturing and video stream visualization.
It provides camera interaction through API Rest or CLI.

### Pre-Requisites

- Python3.10 or higher is required.
- Pre-configured IP addresses on Basler cameras are required. The Pylon IP Configurator app, is provided by the Basler pylon Software Suite.
  Download it at: [https://www.baslerweb.com/en/downloads/software/?srsltid=AfmBOorhg4eoJa0glsNgQvtT9hNgEiwgYKa_75ahCTvJ84nN8cgmwdKj].
  And see the documentation to assign Ip addresses at: [https://docs.baslerweb.com/assigning-an-ip-address-to-a-camera]
- For QRCode detection, install the JDK at: https://www.oracle.com/java/technologies/downloads/

### Installation
There is no need for an installation. A virtual environment with all the required dependencies is automatically activated (and installed if not present) when running the scripts.

### Run as API Rest service

- Start the server running the *start_server* script (.sh for Linux, .bat for Windows)
- List configured cameras with the endpoint "IpAddress/list_cameras". It is useful to see camera data, such as the CAMERA_IDENTIFIER for each camera, that is needed to capture images.
- List detectable cameras with the endpoint "IpAddress/list_cameras_detected". It is useful to check if available cameras are different from the configured ones.
- If cameras are added/removed from the network, save the new configuration with "IpAddress/configure_cameras"
- To capture an image relative to a camera, use the endpoint "IpAddress/camera/CAMERA_IDENTIFIER".
- To show the information about the last image captured from a specific camera, use the endpoint "IpAddress/camera/CAMERA_IDENTIFIER/image_info".
- To show the information about a specific camera, use the endpoint "IpAddress/camera/camera_info".
- To set the rotation value for a specific camera, use the endpoint "IpAddress/set_rotation/CAMERA_IDENTIFIER/ROTATION", Where ROTATION is an int value in the set {0, 90, 180, 270}, describing the rotation angle in degrees in the clockwise direction.
- To set the default exposure time value for a specific camera, use the endpoint "IpAddress/set_exposure/CAMERA_IDENTIFIER/EXPOSURE_TIME", Where EXPOSURE_TIME is the integration time for cameras expressed in microseconds. An higher value makes captured images more bright. The proper value depends on how much the location is illuminated. If images are too bright or dark, try to adjust this parameter. The valid exposure time ranges for specific cameras are available at [https://docs.baslerweb.com/exposure-time]
- To change a camera identifier, use the endpoint "IpAddress/change_iden/OLD_CAMERA_IDENTIFIER/NEW_CAMERA_IDENTIFIER".
- To decode qrcodes of the last image of a camera, use the endpoint "IpAddress/camera/CAMERA_IDENTIFIER/qrcodes".



###### Customize camera configuration.
To customize camera identifiers, exposure times and image rotation values, the file *data/camera_data.json* has to be edited.
- The *rotation* value, has to be an int value in the set {0, 90, 180, 270}, specifying the angle in degrees to rotate an image in the clockwise direction.
- the *exposure_time* value, is the integration time for cameras expressed in microseconds. An higher value makes captured images more bright. The proper value depends on how much the location is illuminated. If images are too bright or dark, try to adjust this parameter. The valid exposure time ranges for specific cameras are available at [https://docs.baslerweb.com/exposure-time]
- The camera identifiers, are the main keys of the file *camera_data.json* file. They can be changed with any string.

### Run with CLI (Command Line Interface)

- Start the CLI by running the *run_cli* script (.sh for Linux, .bat for Windows)
- Type *help* or *?* to list the available commands. With *? COMMAND* where COMMAND is an available command, a short description of such command will be displayed.

