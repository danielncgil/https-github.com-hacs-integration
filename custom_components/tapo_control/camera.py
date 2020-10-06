from homeassistant.helpers.config_validation import boolean
from .const import *
from homeassistant.core import HomeAssistant
from homeassistant.const import (CONF_IP_ADDRESS, CONF_USERNAME, CONF_PASSWORD)
from typing import Callable
from pytapo import Tapo
from homeassistant.util import slugify
from homeassistant.helpers import entity_platform
from homeassistant.components.camera import SUPPORT_STREAM, Camera
from .utils import getCamData
import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: dict, async_add_entities: Callable):
    platform = entity_platform.current_platform.get()
    platform.async_register_entity_service(
        SERVICE_SET_LED_MODE, SCHEMA_SERVICE_SET_LED_MODE, "set_led_mode",
    )
    platform.async_register_entity_service(
        SERVICE_SET_PRIVACY_MODE, SCHEMA_SERVICE_SET_PRIVACY_MODE, "set_privacy_mode",
    )
    platform.async_register_entity_service(
        SERVICE_PTZ, SCHEMA_SERVICE_PTZ, "ptz",
    )
    platform.async_register_entity_service(
        SERVICE_SET_ALARM_MODE, SCHEMA_SERVICE_SET_ALARM_MODE, "set_alarm_mode",
    )
    platform.async_register_entity_service(
        SERVICE_SET_MOTION_DETECTION_MODE, SCHEMA_SERVICE_SET_MOTION_DETECTION_MODE, "set_motion_detection_mode",
    )
    platform.async_register_entity_service(
        SERVICE_SET_AUTO_TRACK_MODE, SCHEMA_SERVICE_SET_AUTO_TRACK_MODE, "set_auto_track_mode",
    )
    platform.async_register_entity_service(
        SERVICE_REBOOT, SCHEMA_SERVICE_REBOOT, "reboot",
    )
    platform.async_register_entity_service(
        SERVICE_SAVE_PRESET, SCHEMA_SERVICE_SAVE_PRESET, "save_preset",
    )
    platform.async_register_entity_service(
        SERVICE_DELETE_PRESET, SCHEMA_SERVICE_DELETE_PRESET, "delete_preset",
    )
    platform.async_register_entity_service(
        SERVICE_FORMAT, SCHEMA_SERVICE_FORMAT, "format",
    )

    camData = await getCamData(hass, hass.data[DOMAIN][entry.entry_id])

    async_add_entities([TapoCamEntity(hass, entry, hass.data[DOMAIN][entry.entry_id],True,camData)])
    async_add_entities([TapoCamEntity(hass, entry, hass.data[DOMAIN][entry.entry_id],False,camData)])



class TapoCamEntity(Camera):
    def __init__(self, hass: HomeAssistant, entry: dict, controller: Tapo, HDStream: boolean, camData):
        super().__init__()
        self._controller = controller
        self._entry = entry
        self._hdstream = HDStream
        self._host = entry.data.get(CONF_IP_ADDRESS)
        self._username = entry.data.get(CONF_USERNAME)
        self._password = entry.data.get(CONF_PASSWORD)

        self.updateCam(camData)
    
    @property
    def supported_features(self):
        return SUPPORT_STREAM

    @property
    def icon(self) -> str:
        return "mdi:cctv"

    @property
    def name(self) -> str:
        return self.getName()

    @property
    def unique_id(self) -> str:
        return self.getUniqueID()

    @property
    def device_state_attributes(self):
        return self._attributes

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state
    
    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, slugify(f"{self._attributes['mac']}_tapo_control"))},
            "name": self._attributes['device_alias'],
            "manufacturer": "TP-Link",
            "model": self._attributes['device_model'],
            "sw_version": self._attributes['sw_version']
        }

    @property
    def motion_detection_enabled(self):
        return self._motion_detection_enabled
    
    @property
    def brand(self):
        return "TP-Link"
    
    @property
    def model(self):
        return self._attributes['device_model']
    
    @property
    def should_poll(self):
        return True

    async def stream_source(self):
        if(self._hdstream):
            streamType = "stream1"
        else:
            streamType = "stream2"
        streamURL = f"rtsp://{self._username}:{self._password}@{self._host}:554/{streamType}"
        return streamURL
    
    async def async_update(self):
        camData = await getCamData(self.hass, self._controller)
        self.updateCam(camData)

    def updateCam(self, camData):
        self._state = "idle"
        self._motion_detection_enabled = camData['motion_detection_enabled']

        self._attributes = camData['basic_info']
        self._attributes['motion_detection_sensitivity'] = camData['motion_detection_sensitivity']
        self._attributes['privacy_mode'] = camData['privacy_mode']
        self._attributes['alarm'] = camData['alarm']
        self._attributes['alarm_mode'] = camData['alarm_mode']
        self._attributes['led'] = camData['led']
        self._attributes['auto_track'] = camData['auto_track']
        self._attributes['presets'] = camData['presets']

    def getName(self):
        name = self._attributes['device_alias']
        if(self._hdstream):
            name += " - HD"
        else:
            name += " - SD"
        return name
    
    def getUniqueID(self):
        if(self._hdstream):
            streamType = "hd"
        else:
            streamType = "sd"
        return slugify(f"{self._attributes['mac']}_{streamType}_tapo_control")


    def ptz(self, tilt = None, pan = None, preset = None, distance = None):
        if preset:
            if(preset.isnumeric()):
                self._controller.setPreset(preset)
            else:
                foundKey = False
                for key, value in self._attributes['presets'].items():
                    if value == preset:
                        foundKey = key
                if(foundKey):
                    self._controller.setPreset(foundKey)
                else:
                    _LOGGER.error("Preset "+preset+" does not exist.")
        elif tilt:
            if distance:
                distance = float(distance)
                if(distance >= 0 and distance <= 1):
                    degrees = 68 * distance
                else:
                    degrees = 5
            else:
                degrees = 5
            if tilt == "UP":
                self._controller.moveMotor(0,degrees)
            else:
                self._controller.moveMotor(0,-degrees)
        elif pan:
            if distance:
                distance = float(distance)
                if(distance >= 0 and distance <= 1):
                    degrees = 360 * distance
                else:
                    degrees = 5
            else:
                degrees = 5
            if pan == "RIGHT":
                self._controller.moveMotor(degrees,0)
            else:
                self._controller.moveMotor(-degrees,0)
        else:
            _LOGGER.error("Incorrect additional PTZ properties. You need to specify at least one of " + TILT + ", " + PAN + ", " + PRESET + ".")

    def set_privacy_mode(self, privacy_mode: str):
        if(privacy_mode == "on"):
            self._controller.setPrivacyMode(True)
        else:
            self._controller.setPrivacyMode(False)
        self.async_schedule_update_ha_state(True)

    def set_alarm_mode(self, alarm_mode, sound = None, light = None):
        if(not light):
            light = "on"
        if(not sound):
            sound = "on"
        if(alarm_mode == "on"):
            self._controller.setAlarm(True, True if sound == "on" else False, True if light == "on" else False)
        else:
            self._controller.setAlarm(False, True if sound == "on" else False, True if light == "on" else False)
        self.async_schedule_update_ha_state(True)

    def set_led_mode(self, led_mode: str):
        if(led_mode == "on"):
            self._controller.setLEDEnabled(True)
        else:
            self._controller.setLEDEnabled(False)
        self.async_schedule_update_ha_state(True)

    def set_motion_detection_mode(self, motion_detection_mode):
        if(motion_detection_mode == "off"):
            self._controller.setMotionDetection(False)
        else:
            self._controller.setMotionDetection(True, motion_detection_mode)
        self.async_schedule_update_ha_state(True)

    def set_auto_track_mode(self, auto_track_mode: str):
        if(auto_track_mode == "on"):
            self._controller.setAutoTrackTarget(True)
        else:
            self._controller.setAutoTrackTarget(False)
        self.async_schedule_update_ha_state(True)

    def reboot(self):
        self._controller.reboot()

    def save_preset(self, name):
        if(not name == "" and not name.isnumeric()):
            self._controller.savePreset(name)
            self.async_schedule_update_ha_state(True)
        else:
            _LOGGER.error("Incorrect "+NAME+" value. It cannot be empty or a number.")

    def delete_preset(self, preset):
        if(preset.isnumeric()):
            self._controller.deletePreset(preset)
            self.async_schedule_update_ha_state(True)
        else:
            foundKey = False
            for key, value in self._attributes['presets'].items():
                if value == preset:
                    foundKey = key
            if(foundKey):
                self._controller.deletePreset(foundKey)
                self.async_schedule_update_ha_state(True)
            else:
                _LOGGER.error("Preset "+preset+" does not exist.")

    def format(self):
        self._controller.format()
                