import { DJILog } from "dji-log-parser-js";
const messageTypes = {
  OSD: {
      expressions: [
          "flyTime",
          "latitude", 
          "longitude",
          "height",
          "heightMax",
          "vpsHeight",
          "altitude",
          "xSpeed",
          "xSpeedMax",
          "ySpeed",
          "ySpeedMax",
          "zSpeed",
          "zSpeedMax",
          "pitch",
          "roll",
          "yaw",
          "flycState",
          "flycCommand",
          "flightAction",
          "isGpdUsed",
          "nonGpsCause",
          "gpsNum",
          "gpsLevel",
          "droneType",
          "isSwaveWork",
          "waveError",
          "goHomeStatus",
          "batteryType",
          "isOnGround",
          "isMotorOn",
          "isMotorBlocked",
          "motorStartFailedCause",
          "isImuPreheated",
          "imuInitFailReason",
          "isAcceletorOverRange",
          "isBarometerDeadInAir",
          "isCompassError",
          "isGoHomeHeightModified",
          "canIocWork",
          "isNotEnoughForce",
          "isOutOfLimit",
          "isPropellerCatapult",
          "isVibrating",
          "isVisionUsed",
          "voltageWarning"
      ]
  },
  gimbal: {
      expressions: [
          "mode",
          "pitch",
          "roll", 
          "yaw",
          "isPitchAtLimit",
          "isRollAtLimit",
          "isYawAtLimit",
          "isStuck"
      ]
  },
  CAMERA: {
      expressions: [
          "isPhoto",
          "isVideo",
          "sdCardIsInserted",
          "sdCardState"
      ]
  },
  RC: {
      expressions: [
          "downlinkSignal",
          "uplinkSignal",
          "aileron",
          "elevator",
          "throttle",
          "rudder"
      ]
  },
  BATTERY: {
      expressions: [
          "chargeLevel",
          "voltage",
          "current",
          "currentCapacity",
          "fullCapacity",
          "cellNum",
          "isCellVoltageEstimated",
          "cellVoltages",
          "cellVoltageDeviation",
          "maxCellVoltageDeviation",
          "temperature",
          "minTemperature",
          "maxTemperature"
      ]
  },
  HOME: {
      expressions: [
          "latitude",
          "longitude",
          "altitude",
          "heightLimit",
          "isHomeRecord",
          "goHomeMode",
          "isDynamicHomePointEnabled",
          "isNearDistanceLimit",
          "isNearHeightLimit",
          "isCompassCalibrating",
          "isMultipleModeEnabled",
          "isBeginnerMode",
          "isIocEnabled",
          "goHomeHeight",
          "maxAllowedHeight",
          "currentFlightRecordIndex"
      ]
  },
  RECOVER: {
      expressions: [
          "appPlatform",
          "appVersion",
          "aircraftName",
          "aircraftSn",
          "cameraSn",
          "rcSn",
          "batterySn"
      ]
  },
  APP: {
      expressions: [
          "tip",
          "warn"
      ]
  }
}

for (const key of Object.keys(messageTypes)) {
  messageTypes[key].complexFields = messageTypes[key].expressions.map(e => {
    return {
      name: e,
      units: "?",
      multiplier: 1
    }
  })
}
function transformData(dataArray, startTime) {
  if (!dataArray || dataArray.length === 0) {
      return {};
  }

  // Helper function to capitalize first letter
  const capitalize = (str) => str.charAt(0).toUpperCase() + str.slice(1).toUpperCase();

  // Initialize the messages object
  const messages = {};

  // First pass: initialize the structure based on the first item
  const firstItem = dataArray[0];
  Object.keys(firstItem).forEach(key => {
      const capitalizedKey = capitalize(key);
      messages[capitalizedKey] = {
          time_boot_ms: []
      };

      // Helper function to initialize arrays for nested objects
      function initializeArraysForObject(obj, targetObj) {
          Object.keys(obj).forEach(nestedKey => {
              if (typeof obj[nestedKey] === "object" && !Array.isArray(obj[nestedKey])) {
                  targetObj[nestedKey] = {};
                  initializeArraysForObject(obj[nestedKey], targetObj[nestedKey]);
              } else {
                  targetObj[nestedKey] = [];
              }
          });
      }

      // Initialize arrays for the current section
      if (firstItem[key] && typeof firstItem[key] === "object") {
          initializeArraysForObject(firstItem[key], messages[capitalizedKey]);
      }
  });

  // Second pass: populate the arrays
  dataArray.forEach(item => {
      const timestamp = new Date(item.custom.dateTime).getTime() - startTime;
      Object.keys(item).forEach(key => {
          const capitalizedKey = capitalize(key);
          if (messages[capitalizedKey]) {
              // Add timestamp to this section
              messages[capitalizedKey].time_boot_ms.push(timestamp);

              // Helper function to populate arrays for nested objects
              function populateArrays(sourceObj, targetObj) {
                  Object.keys(sourceObj).forEach(nestedKey => {
                      if (typeof sourceObj[nestedKey] === "object" && !Array.isArray(sourceObj[nestedKey])) {
                          populateArrays(sourceObj[nestedKey], targetObj[nestedKey]);
                      } else if (targetObj[nestedKey]) { // Check if the target array exists
                          targetObj[nestedKey].push(sourceObj[nestedKey]);
                      }
                  });
              }

              // Populate arrays for the current section
              if (item[key] && typeof item[key] === "object") {
                  populateArrays(item[key], messages[capitalizedKey]);
              }
          }
      });
  });
  console.log(messages)
  return messages;
}

class DjiParser {
  
    loadType() {
      console.warn("DjiParser.loadType() is not implemented")
    }

    async processData(data) { 
      const parser = new DJILog(new Uint8Array(data));
      const keychains = await parser.fetchKeychains(
        "f05e96fa44f3f36eb9962948bac0f77",
        "//proxy.galvanicloop.com/https://dev.dji.com/openapi/v1/flight-records/keychains"
      );
      const frames = parser.frames(keychains)
      const startTime = new Date(frames[0].custom.dateTime).getTime()
      self.postMessage({ metadata: {startTime: new Date(frames[0].custom.dateTime).getTime()}})
      self.postMessage({ availableMessages: messageTypes })
      self.postMessage({ messages: transformData(frames, startTime) })
      self.postMessage({ messagesDoneLoading: true })

    }
}
export default DjiParser