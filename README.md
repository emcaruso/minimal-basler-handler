#  Minimal Basler Handler

A simple library to interact with Basler Cameras. It provides image capturing and video stream visualization.

### Pre-Requisites

- Linux OS and Python3 are required.

- Pre-configured IP addresses on Basler cameras are required. The Pylon IP Configurator provided by the Pylon SDK can be used: [https://docs.baslerweb.com/software-installation-(linux)].

### Demo

A CLI for demonstrations can be executed by running the bash script *run.sh*. The CLI leverages the BaslerHandler class defined in the *basler_handler.py* file.

To get a more detailed description of the available commands, type *help*, followed by the command.

## Camera Configuration

To acquire images inside the CLI, first a camera configuration is needed by executing the *configure_cameras* command. It will assign ids to available cameras and will store the configuration.

The current configuration can be diplayed with the *list_cameras* command.

All commands for image capturing and video stream visualization rely on camera ids belonging to the saved configuration.

To make a new configuration, just redo the *configure_cameras* command.

## Show camera stream

To show the camera stream, use the *show_camera_stream* command, passing the camera id as argument. The stream will be displayed until the user presses the Q key.

## Capture images

To capture images, use the *grab_images* command, passing the camera ids and the exposure time. The grabbed images will be stored on disk.

To a better description of the command, type *help grab_images*

To list information about all the stored images, use the *list_images* command.

To show all the stored images, use the *show_images* command.

To rmove all the stored images, use the *remove_images* command.

