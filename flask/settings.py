import os
import json

_SETTINGS = None


def get_settings_path():
    # when usb stick is not installed (e.g. for pytest), start with:
    # sudo LRPI_SETTINGS_PATH=/home/inbrewj/workshop/LushRooms/faux_usb/settings.json python3 -u flask/Server.py

    SETTINGS_PATH = os.environ.get(
        "LRPI_SETTINGS_PATH", "/media/usb/settings.json")

    return SETTINGS_PATH


def get_settings():

    global _SETTINGS

    if _SETTINGS is None:
        if os.path.exists(get_settings_path()):
            with open(get_settings_path()) as f:
                _SETTINGS = get_combined_settings()

    return _SETTINGS


def get_combined_settings():
    """
    In order of precedence:
    json
    envar
    default
    """

    json_settings = get_json_settings()
    env_settings = get_evn_settings()

    combined = env_settings.copy()

    for k in env_settings.keys():
        if json_settings.get(k):
            combined[k] = json_settings[k]

    print("***********  SETTINGS  ***********")
    print(json.dumps(combined, indent=4))

    return combined


def get_json_settings():

    if os.path.exists(get_settings_path()):
        with open(get_settings_path()) as f:
            return json.loads(f.read())
    return None


def get_evn_settings():

    settings = {}
    settings["name"] = os.environ.get("NAME", "?")
    settings["hue_ip"] = os.environ.get("HUE_IP", "")
    settings["hue_bridge_id"] = os.environ.get("HUE_BRIDGE_ID")
    settings["hue_name"] = os.environ.get("HUE_NAME", "")
    settings["hue_brightness"] = os.environ.get("HUE_BRIGHTNESS", "254")
    settings["dmx_brightness"] = os.environ.get("DMX_BRIGHTNESS", "254")
    settings["fade_interval"] = os.environ.get("FADE_INTERVAL", "5")
    settings["paired"] = os.environ.get("PAIRED", "")
    settings["slave_ip"] = os.environ.get("SLAVE_IP", "")
    settings["debug"] = os.environ.get("DEBUG") == "true"
    settings["audio_volume"] = int(os.environ.get("AUDIO_VOLUME", "100"))
    settings["audio_output"] = os.environ.get("AUDIO_OUPUT", "hdmi")
    settings["activate_idle_loop"] = os.environ.get(
        "ACTIVATE_IDLE_LOOP", "true")
    settings["reset_dmx_command"] = os.environ.get(
        "RESET_DMX_COMMAND", "DMX1(20,20,20,20,20,20,20,20)")
    settings["reset_hue_command"] = os.environ.get(
        "RESET_HUE_COMMAND", "{'transitiontime' : 5, 'on' : True, 'bri' : 50, 'sat' : 100, 'hue' : 0, 'ct' : 450}")
    settings["media_base_path"] = os.environ.get(
        "MEDIA_BASE_PATH", "/media/usb/tracks/")
    return settings
