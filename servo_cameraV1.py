import serial
import time
import sys

print("ESP32-C3 Photo + Filter Control")
print("--------------------------------")

try:
    ser = serial.Serial('COM7', 115200, timeout=1)
    time.sleep(2)

    print("Connected. Press Enter to capture both photos")
    print("Press Ctrl+C to exit")

    while True:
        input("Press Enter to start capture sequence")

        def send_cmd(cmd):
            ser.write((cmd + '\n').encode())
            time.sleep(0.5)
            if ser.in_waiting:
                print("ESP32:", ser.read(ser.in_waiting).decode().strip())

        # Step 1: Take photo without filter
        send_cmd("SHUTTER")

        # Step 2: Move filter in front
        send_cmd("FILTER,ON")
        time.sleep(1)

        # Step 3: Take photo with filter
        send_cmd("SHUTTER")

        # Step 4: Move filter away
        send_cmd("FILTER,OFF")

except serial.SerialException as e:
    print(f"Serial error: {e}")
    sys.exit(1)
except KeyboardInterrupt:
    print("Exiting...")
finally:
    try:
        ser.close()
    except:
        pass
