### MAVLink Context for LLM

This file provides a high-level overview of important MAVLink messages for a flight data analysis agent.

**Key Message Types:**

*   **`GPS`**: Global Positioning System data.
    *   `Status`: GPS fix status (0-1: No Fix, 2: 2D Fix, 3: 3D Fix, 4: DGPS, 5: RTK Float, 6: RTK Fixed). A status `< 3` is generally considered a poor lock for flight.
    *   `NSats`: Number of satellites visible. More is better.
    *   `Alt`: Altitude above mean sea level.
    *   `Lat`, `Lng`: Latitude and Longitude.
    *   `TimeUS`: Timestamp in microseconds, useful for calculating duration.

*   **`BARO`**: Barometer data.
    *   `Alt`: Barometric altitude. Often more stable for relative altitude changes than GPS.
    *   `Press`: Absolute pressure.
    *   `Temp`: Air temperature.

*   **`ATT` (Attitude):**
    *   `Roll`, `Pitch`, `Yaw`: The orientation of the vehicle in degrees. Sudden, large changes can indicate instability.

*   **`IMU` (Inertial Measurement Unit):**
    *   `AccX`, `AccY`, `AccZ`: Accelerometer data. High values can indicate high vibrations or a crash.
    *   `GyrX`, `GyrY`, `GyrZ`: Gyroscope data.

*   **`BAT` (Battery):**
    *   `Volt`: Battery voltage. A sudden drop can indicate a battery failure.
    *   `Curr`: Battery current draw.
    *   `Temp`: Battery temperature. High temperatures are dangerous.

*   **`ERR` (Error):**
    *   `Subsys`: The subsystem that generated the error (e.g., GPS, Baro, Compass).
    *   `ECode`: The specific error code.

*   **`EV` (Event):**
    *   `Id`: The event ID. `10` for Armed, `11` for Disarmed, `26` for RC_FAILSAFE.

**Common Analysis Tasks:**

*   **Flight Time:** Calculate from the difference between the first and last `GPS.TimeUS`.
*   **Max Altitude:** Find the maximum value of `GPS.Alt` or `BARO.Alt`.
*   **GPS Issues:** Look for `GPS.Status < 3` or a low `GPS.NSats`.
*   **Critical Errors:** Scan for all `ERR` messages and report their subsystems and error codes.
*   **RC Signal Loss:** Look for `EV.Id == 26` (RC_FAILSAFE). 