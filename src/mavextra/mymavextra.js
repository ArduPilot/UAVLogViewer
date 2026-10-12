// const key = ''
// const last_value = 0
globalThis.named = (NAMED_VALUE_FLOAT, key) => {
    if (NAMED_VALUE_FLOAT.name.startsWith(key)) {
        return NAMED_VALUE_FLOAT.value;
    }
    return null;
};

// eslint-disable-next-line camelcase
globalThis.angle_diff = (angle1, angle2) => {
    let ret = angle1 - angle2;
    if (ret > 180) {
        ret -= 360;
    }
    if (ret < -180) {
        ret += 360;
    }
    return ret;
};

// eslint-disable-next-line camelcase
globalThis.wrap_360 = (angle) => {
    let ret = angle;
    if (ret > 360) {
        ret -= 360;
    }
    if (ret < 0) {
        ret += 360;
    }
    return ret;
};

// eslint-disable-next-line camelcase
globalThis.wrap_180 = (angle) => {
    let ret = angle;
    if (ret > 180) {
        ret -= 360;
    }
    if (ret < -180) {
        ret += 360;
    }
    return ret;
};

globalThis.min = Math.min;
globalThis.max = Math.max;
