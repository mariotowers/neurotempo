# scripts/test_muse_eeg.py
import time

from neurotempo.brain.brainflow_muse import BrainFlowMuseBrain, MuseNotReady


def main():
    device_id = "7159EEF5-52BA-D787-7F30-636806BD9424"  # from muselsl list (macOS UUID)
    brain = BrainFlowMuseBrain(device_id=device_id, timeout_s=15.0, window_sec=2.0, enable_logs=True)

    try:
        print("Starting Muse auto-connect…")
        brain.start()
        print("✅ Connected. Reading 15 samples…")

        for i in range(15):
            m = brain.read_metrics()
            print(f"{i:02d} focus={m.focus:.3f}  fatigue={m.fatigue:.3f}  HR={m.heart_rate}  SpO2={m.spo2}")
            time.sleep(1)

    except MuseNotReady as e:
        print("❌ Muse not ready:", e)
        print("Tips: turn Muse on, wear it, ensure Bluetooth on, and close other Muse apps.")
    finally:
        brain.stop()
        print("Stopped.")


if __name__ == "__main__":
    main()