from pypylon import pylon, genicam


def set_auto_target(camera: pylon.InstantCamera, target: int):

    try:
        val = max(int(target*255),50)
        camera.AutoTargetValue.Value = val
    except:
        try:
            camera.AutoTargetBrightness.Value = target
        except:
            import ipdb; ipdb.set_trace()
            pass


def white_balancing(camera: pylon.InstantCamera, on: bool):

    try:
        if on:
            camera.BalanceWhiteAuto.Value = "Continuous"
        else:
            camera.BalanceWhiteAuto.Value = "Off"
    except:
        pass
    pass


def set_gamma(camera: pylon.InstantCamera, gamma: float):
    try:
        camera.GammaSelector.Value = "User"
        camera.GammaEnable.Value = True
        camera.Gamma.Value = gamma
    except:
        pass
    


def remove_autogain(camera: pylon.InstantCamera):
    try:
        camera.GainAuto.Value = "Off"
    except:
        pass

    try:
        camera.Gain.Value = 0
    except:
        try:
            camera.GainRaw.Value = 0
        except:
            pass


def set_autoexposure(
    camera: pylon.InstantCamera,
    brightness_val: int,
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
    #

    set_auto_target(camera, brightness_val)
    # camera.AutoFunctionROISelector.Value = "ROI1"
    # camera.AutoFunctionProfile.Value = "MinimizeExposureTime"
    camera.ExposureAuto.Value = "Continuous"
    # camera.GainAuto.Value = "Continuous"
    # camera.BslColorSpace.Value = "Off"
    converter = pylon.ImageFormatConverter()
    converter.OutputPixelFormat = pylon.PixelType_BGR8packed
    for i in range(12):
        grabResult = camera.RetrieveResult(
            timeout, pylon.TimeoutHandling_ThrowException
        )
        if grabResult.GrabSucceeded():
            img = converter.Convert(grabResult).GetArray()
            brightness = img.mean() / 255
            # print(brightness)
            # print(brightness)

            # # custom thresholding
            # if abs(brightness - brightness_val) < brightness_thresh:
            #     camera.ExposureAuto.Value = "Off"
            #     camera.GainAuto.Value = "Off"
            #     break
            #
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

    exposure_time = min(max(30, exposure_time), 999999)
    camera.ExposureAuto.Value = "Off"
    camera.GainAuto.Value = "Off"
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
