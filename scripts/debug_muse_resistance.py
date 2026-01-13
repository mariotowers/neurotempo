import time
import numpy as np

from brainflow.board_shim import BoardShim
from neurotempo.brain.brainflow_muse import BrainFlowMuseBrain, MuseNotReady


def main():
    brain = BrainFlowMuseBrain(device_id=None, timeout_s=15.0, window_sec=2.0, enable_logs=False)

    print("Connecting to Muse…")
    try:
        brain.start()
    except MuseNotReady as e:
        print("Muse not ready:", e)
        return

    board = brain.board
    board_id = brain.board_id
    print("✅ Connected")
    print("board_id:", board_id)
    print("eeg_channels:", brain.eeg_channels)
    print("fs:", brain.fs)

    # Resistance channels (if supported)
    try:
        res_ch = BoardShim.get_resistance_channels(board_id)
        res_ch = list(res_ch) if res_ch else []
    except Exception as e:
        res_ch = []
        print("get_resistance_channels() error:", repr(e))

    print("resistance_channels:", res_ch)

    # Pull a small buffer and print medians
    time.sleep(1.0)
    raw = board.get_current_board_data(32)
    print("raw shape:", raw.shape)

    if res_ch:
        r = raw[res_ch, :].astype(np.float64)
        med = np.nanmedian(r, axis=1)
        print("Resistance medians (ohms):", [float(x) for x in med])
    else:
        print("❌ No resistance channels exposed on this setup (will fallback).")

    # Also show EEG stds (so we can tune fallback)
    eeg = raw[brain.eeg_channels, :].astype(np.float64)
    eeg = eeg - np.mean(eeg, axis=1, keepdims=True)
    stds = np.std(eeg, axis=1)
    print("EEG stds:", [float(x) for x in stds])

    brain.stop()
    print("Stopped.")


if __name__ == "__main__":
    main()