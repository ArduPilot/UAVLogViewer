require('mavlink_common_v1.0/mavlink')

let modeMappingApm = {
  0: 'MANUAL',
  1: 'CIRCLE',
  2: 'STABILIZE',
  3: 'TRAINING',
  4: 'ACRO',
  5: 'FBWA',
  6: 'FBWB',
  7: 'CRUISE',
  8: 'AUTOTUNE',
  10: 'AUTO',
  11: 'RTL',
  12: 'LOITER',
  14: 'LAND',
  15: 'GUIDED',
  16: 'INITIALISING',
  17: 'QSTABILIZE',
  18: 'QHOVER',
  19: 'QLOITER',
  20: 'QLAND',
  21: 'QRTL'
}
let modeMappingAcm = {
  0: 'STABILIZE',
  1: 'ACRO',
  2: 'ALT_HOLD',
  3: 'AUTO',
  4: 'GUIDED',
  5: 'LOITER',
  6: 'RTL',
  7: 'CIRCLE',
  8: 'POSITION',
  9: 'LAND',
  10: 'OF_LOITER',
  11: 'DRIFT',
  13: 'SPORT',
  14: 'FLIP',
  15: 'AUTOTUNE',
  16: 'POSHOLD',
  17: 'BRAKE',
  18: 'THROW',
  19: 'AVOID_ADSB',
  20: 'GUIDED_NOGPS',
  21: 'SMART_RTL'
}
let modeMappingRover = {
  0: 'MANUAL',
  2: 'LEARNING',
  3: 'STEERING',
  4: 'HOLD',
  10: 'AUTO',
  11: 'RTL',
  12: 'SMART_RTL',
  15: 'GUIDED',
  16: 'INITIALISING'
}

let modeMappingTracker = {
  0: 'MANUAL',
  1: 'STOP',
  2: 'SCAN',
  10: 'AUTO',
  16: 'INITIALISING'
}

let modeMappingSub = {
  0: 'STABILIZE',
  1: 'ACRO',
  2: 'ALT_HOLD',
  3: 'AUTO',
  4: 'GUIDED',
  7: 'CIRCLE',
  9: 'SURFACE',
  16: 'POSHOLD',
  19: 'MANUAL'
}

function getModeMap (mavType) {
  let map
  if ([mavlink.MAV_TYPE_QUADROTOR,
    mavlink.MAV_TYPE_HELICOPTER,
    mavlink.MAV_TYPE_HEXAROTOR,
    mavlink.MAV_TYPE_OCTOROTOR,
    mavlink.MAV_TYPE_COAXIAL,
    mavlink.MAV_TYPE_TRICOPTER].includes(mavType)) {
    map = modeMappingAcm
  }
  if (mavType === mavlink.MAV_TYPE_FIXED_WING) {
    map = modeMappingApm
  }
  if (mavType === mavlink.MAV_TYPE_GROUND_ROVER) {
    map = modeMappingRover
  }
  if (mavType === mavlink.MAV_TYPE_ANTENNA_TRACKER) {
    map = modeMappingTracker
  }
  if (mavType === mavlink.MAV_TYPE_SUBMARINE) {
    map = modeMappingSub
  }
  if (map == null) {
    return null
  }
  return map
}


function assign_column (obj) {
  var ArrayOfString = obj.split(',')
  return ArrayOfString
}

// Converts from degrees to radians.
Math.radians = function (degrees) {
  return degrees * Math.PI / 180
}

// Converts from radians to degrees.
Math.degrees = function (radians) {
  return radians * 180 / Math.PI
}

export class DataflashParser {
  constructor () {
    this.time = null
    this.timebase = null
    this.buffer = null
    this.data = null
    this.FMT = []
    this.FMT[128] = {'Type': '128', 'length': '89', 'Name': 'FMT', 'Format': 'BBnNZ', 'Columns': 'Type,Length,Name,Format,Columns'}
    this.offset = 0
    this.msgType = []
    this.offsetArray = []
    this.totalSize = null
    this.messages = {}
    this.lastPercentage = 0
    this.sent = false
    this.maxPercentageInterval = 0.05
  }

  FORMAT_TO_STRUCT (obj) {
    var temp
    var dict = {
      name: obj.Name,
      fieldnames: obj.Columns.split(',')
    }

    var column = assign_column(obj.Columns)
    for (var i = 0; i < obj.Format.length; i++) {
      temp = obj.Format.charAt(i)
      switch (temp) {
        case 'b':
          dict[column[i]] = this.data.getInt8(this.offset)
          this.offset += 1
          break
        case 'B':
          dict[column[i]] = this.data.getUint8(this.offset)
          this.offset += 1
          break
        case 'h':
          dict[column[i]] = this.data.getInt16(this.offset, true)
          this.offset += 2
          break
        case 'H':
          dict[column[i]] = this.data.getUint16(this.offset, true)
          this.offset += 2
          break
        case 'i':
          dict[column[i]] = this.data.getInt32(this.offset, true)
          this.offset += 4
          break
        case 'I':
          dict[column[i]] = this.data.getUint32(this.offset, true)
          this.offset += 4
          break
        case 'f':
          dict[column[i]] = this.data.getFloat32(this.offset, true)
          this.offset += 4
          break
        case 'd':
          dict[column[i]] = this.data.getFloat64(this.offset, true)
          this.offset += 8
          break
        case 'Q':
          var low = this.data.getUint32(this.offset, true)
          this.offset += 4
          var n = this.data.getUint32(this.offset, true) * 4294967296.0 + low
          if (low < 0) n += 4294967296
          dict[column[i]] = n
          this.offset += 4
          break
        case 'q':
          var low = this.data.getInt32(this.offset, true)
          this.offset += 4
          var n = this.data.getInt32(this.offset, true) * 4294967296.0 + low
          if (low < 0) n += 4294967296
          dict[column[i]] = n
          this.offset += 4
          break
        case 'n':
          dict[column[i]] = String.fromCharCode.apply(null, new Uint8Array(this.buffer, this.offset, 4)).replace(/\x00+$/g, '')
          this.offset += 4
          break
        case 'N':
          dict[column[i]] = String.fromCharCode.apply(null, new Uint8Array(this.buffer, this.offset, 16)).replace(/\x00+$/g, '')
          this.offset += 16
          break
        case 'Z':
          dict[column[i]] = String.fromCharCode.apply(null, new Uint8Array(this.buffer, this.offset, 64)).replace(/\x00+$/g, '')
          this.offset += 64
          break
        case 'c':
          // this.this.data.setInt16(offset,true);
          dict[column[i]] = this.data.getInt16(this.offset, true) * 100
          this.offset += 2
          break
        case 'C':
          // this.data.setUint16(offset,true);
          dict[column[i]] = this.data.getUint16(this.offset, true) * 100
          this.offset += 2
          break
        case 'E':
          // this.data.setUint32(offset,true);
          dict[column[i]] = this.data.getUint32(this.offset, true) * 100
          this.offset += 4
          break
        case 'e':
          // this.data.setInt32(offset,true);
          dict[column[i]] = this.data.getInt32(this.offset, true) * 100
          this.offset += 4
          break
        case 'L':
          // this.data.setInt32(offset,true);
          dict[column[i]] = this.data.getInt32(this.offset, true)
          this.offset += 4
          break
        case 'M':
          // this.data.setInt32(offset,true);
          dict[column[i]] = this.data.getUint8(this.offset)
          this.offset += 1
          break
      }
    }
    return dict
  }

  gpstimetoTime (week, msec) {
    let epoch = 86400 * (10 * 365 + (1980 - 1969) / 4 + 1 + 6 - 2)
    return epoch + 86400 * 7 * week + msec * 0.001 - 15
  }

  setTimeBase (base) {
    this.timebase = base
  }

  findTimeBase (gps) {
    var temp = this.gpstimetoTime(parseInt(gps['GWk']), parseInt(gps['GMS']))
    this.setTimeBase(parseInt(temp - gps['TimeUS'] * 0.000001))
  }

  getMsgType=function (element) {
    for (i = 0; i < this.FMT.length; i++) {
      if (this.FMT[i] != null) {
        if (this.FMT[i].Name == element) {
          return i
        }
      }
    }
  }

  onMessage (message) {
    if (this.totalSize == null) { // for percentage calculation
      this.totalSize = this.buffer.byteLength
    }

    if (message.name in this.messages) {
      this.messages[message.name].push(this.fixData(message))
    } else {
      this.messages[message.name] = [this.fixData(message)]
    }
    let percentage = 100 * this.offset / this.totalSize
    if ((percentage - this.lastPercentage) > this.maxPercentageInterval) {
      self.postMessage({percentage: percentage})
      this.lastPercentage = percentage
    }

    // TODO: FIX THIS!
    // This a hack to detect the end of the buffer and only them message the main thread
    if ((this.totalSize - this.offset) < 100 && this.sent === false) {
      self.postMessage({percentage: 100})
      self.postMessage({messages: this.messages})
      this.sent = true
    }
  }

  parse_atOffset (type, name) {
    type = this.getMsgType(type)
    var parsed = []
    var num = 0
    for (var i = 0; i < this.msgType.length; i++) {
      if (type == this.msgType[i]) {
        this.offset = this.offsetArray[i]
        var temp = this.FORMAT_TO_STRUCT(this.FMT[this.msgType[i]])
        if (name == 'TimeUS' && temp[name] != null) {
          parsed.push(this.time_stamp(temp[name]))
        } else if (temp[name] != null) {
          parsed.push(temp[name])
        }
      }
    }
    return parsed
  }

  time_stamp (TimeUs) {
    var temp = 0
    temp = this.timebase + TimeUs * 0.000001
    if (temp > 0) { TimeUs = temp }
    var date = new Date(TimeUs * 1000)
    var day = date.getDate()
    var month = date.getMonth()
    var year = date.getFullYear()
    var hours = date.getHours()
    var minutes = '0' + date.getMinutes()
    var seconds = '0' + date.getSeconds()
    var formattedTime = hours + ':' + minutes.substr(-2) + ':' + seconds.substr(-2)
    var date = date.toString()
    var time = date.split(' ')
    if (time[0] !== 'Invalid') {
      this.time = time[0] + ' ' + time[1] + ' ' + time[2] + ' ' + time[3]
    }
    return formattedTime
  }

  DF_reader () {
    while (this.offset < (this.buffer.byteLength - 20)) {
      this.offset += 2
      var attribute = this.data.getUint8(this.offset)
      if (this.FMT[attribute] != null) {
        this.offset += 1
        this.offsetArray.push(this.offset)
        this.msgType.push(attribute)
        var value = this.FORMAT_TO_STRUCT(this.FMT[attribute])
        if (this.FMT[attribute].Name == 'GPS') {
          this.findTimeBase(value)
        }
        if (attribute == '128') {
          this.FMT[value['Type']] = {
            'Type': value['Type'],
            'length': value['Length'],
            'Name': value['Name'],
            'Format': value['Format'],
            'Columns': value['Columns']
          }
        }
        this.onMessage(value)
      } else {
        this.offset += 1
      }
    }
  }
  getModeString (cmode) {
    let mavtype
    if (this.messages['MSG'][0].Message.indexOf('ArduPlane')>-1) {
      mavtype = mavlink.MAV_TYPE_FIXED_WING
    } else if (this.messages['MSG'][0].indexOf('ArduCopter')>-1) {
      mavtype = mavlink.MAV_TYPE_QUADROTOR
    } else if (this.messages['MSG'][0].indexOf('ArduSub')>-1) {
      mavtype = mavlink.MAV_TYPE_SUBMARINE
    } else if (this.messages['MSG'][0].indexOf('Rover')>-1) {
      mavtype = mavlink.MAV_TYPE_GROUND_ROVER
    } else if (this.messages['MSG'][0].indexOf('Tracker')>-1) {
      mavtype = mavlink.MAV_TYPE_ANTENNA_TRACKER
    }
    return getModeMap(mavtype)[cmode]
  }

  fixData (message) {
    if (message.name === 'GPS') {
      message.Lat = message.Lat / 1e7
      message.Lng = message.Lng / 1e7
      message.Alt = message.Alt / 1e4
    } else if (message.name === 'ATT') {
      message.Roll = Math.radians(message.Roll / 1e4)
      message.Pitch = Math.radians(message.Pitch / 1e4)
      message.Yaw = Math.radians(message.Yaw / 1e4)
    } else if (message.name === 'MODE') {
      message.asText = this.getModeString(message.Mode)
    }
    message.time_boot_ms = message.TimeUS / 1000
    return message
  }

  processData (data) {
    this.buffer = Buffer.from(data).buffer
    this.data = new DataView(this.buffer)
    this.DF_reader()
  }
}
