"""List available audio devices."""

import sounddevice as sd

def list_devices():
    print("\n=== Available Audio Devices ===\n")
    print(sd.query_devices())
    print("\n===============================\n")
    
    default_input = sd.query_devices(kind='input')
    print(f"Default Input Device: {default_input['name']} (Index: {default_input['index']})")

if __name__ == "__main__":
    try:
        list_devices()
    except Exception as e:
        print(f"Error listing devices: {e}")
