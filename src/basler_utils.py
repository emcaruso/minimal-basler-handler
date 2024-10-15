from pypylon import pylon, genicam


def set_autotarget(cmaera: pylon.InstantCamera, target: int):
    try:
        camera.AutoTargetValue.Value = target
    except:
        camera.AutoTargetBrightness.Value = target


def set_autoexposure(
    camera: pylon.InstantCamera,
    brightness_val: int,
    brightness_thresh: int,
    timeout: int,
):
    """
    Set auto exposure and gain to reach a target brightness value
    """

    # camera.BslLightSourcePreset.Value = "Off"
    # minLowerLimit = camera.AutoExposureTimeLowerLimit.Min
    # maxUpperLimit = camera.AutoExposureTimeUpperLimit.Max
    # camera.AutoExposureTimeLowerLimit.Value = minLowerLimit
    # camera.AutoExposureTimeUpperLimit.Value = maxUpperLimit

    set_auto_target(camera, brightness_val)
    # camera.AutoFunctionROISelector.Value = "ROI1"
    # camera.AutoFunctionProfile.Value = "MinimizeExposureTime"
    # camera.ExposureAuto.Value = "Once"
    # camera.GainAuto.Value = "Once"
    # camera.BslColorSpace.Value = "Off"
    converter = pylon.ImageFormatConverter()
    converter.OutputPixelFormat = pylon.PixelType_BGR8packed
    while camera.ExposureAuto.Value == "Once" or camera.GainAuto.Value == "Once":
        grabResult = camera.RetrieveResult(
            timeout, pylon.TimeoutHandling_ThrowException
        )
        if grabResult.GrabSucceeded():
            img = converter.Convert(grabResult).GetArray()
            brightness = img.mean() / 255
            print(brightness)

            # custom thresholding
            if abs(brightness - brightness_val) < brightness_thresh:
                camera.ExposureAuto.Value = "Off"
                camera.GainAuto.Value = "Off"
                break

    # camera.BslLightSourcePresetFeatureEnable.Value = False
    # camera.BslColorSpace.Value = "sRgb"


def get_exposure(camera: pylon.InstantCamera):
    try:
        exposure_time = camera.ExposureTime.Value
    except:
        exposure_time = camera.ExposureTimeAbs.Value
    return exposure_time


def set_exposure(camera: pylon.InstantCamera, exposure_time: int):
    """
    set_exposure time for a camera
    """
    try:
        if camera.ExposureTime.Value != exposure_time:
            camera.ExposureTime.Value = exposure_time
    except:
        if camera.ExposureTimeAbs.Value != exposure_time:
            camera.ExposureTimeAbs.Value = exposure_time

    # camera.BslLightSourcePreset.Value = "Off"
    # camera.BslLightSourcePresetFeatureEnable.Value = False
    # camera.BslColorSpace.Value = "sRgb"


def set_fps(camera: pylon.InstantCamera, fps: int) -> None:
    """
    set fps rate for a camera
    """
    pass
    #
    # period = int((1 / fps) * 1e6)
    # camera.BslPeriodicSignalPeriod.Value = period
    # camera.BslPeriodicSignalDelay.Value = 0
    # camera.TriggerSelector.Value = "FrameStart"
    # camera.TriggerMode.Value = "On"
    # camera.TriggerSource.Value = "PeriodicSignal1"
