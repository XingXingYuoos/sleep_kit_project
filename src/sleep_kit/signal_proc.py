"""
sleep_kit.signal_proc
=====================

Core signal processing utilities for PSG channels.

This module implements the standardized preprocessing pipeline used in SleepKit.
Each channel undergoes:

1. Channel selection (pick)
2. Re-referencing
3. Filtering (notch + bandpass)
4. Resampling
5. Unit normalization (Volt ↔ microvolt)

The logic directly follows the original data preparation workflow
(`read_data.py` in the reference codebase), ensuring full compatibility
with existing preprocessing standards.
"""

import numpy as np
import mne


def process_single_channel(raw, ch_name, ref_name=None,
                           target_fs=100, filter_cfg=None):
    """
    Process a single PSG channel with the following steps:
    Pick → Rereference → Filter → Resample → Unit normalization.

    Parameters
    ----------
    raw : mne.io.Raw
        Loaded PSG signal.
    ch_name : str
        Name of the target channel to extract.
    ref_name : str or None, optional
        Name of the reference channel for re-referencing.
        If None, no referencing is applied.
    target_fs : int, optional
        Target sampling frequency. Default is ``100``.
    filter_cfg : dict or None, optional
        Filtering configuration dictionary with keys:

            - ``'bp'`` : [low, high] bandpass cutoff
            - ``'notch'`` : list of notch frequencies

        Example:
            ``{'bp': [0.3, 35], 'notch': [50, 60]}``

    Returns
    -------
    data : ndarray or None
        1-D NumPy array of processed samples.
        Returns None if channel missing or any processing error occurs.

    Notes
    -----
    - Rereferencing is applied only if ``ref_name`` is provided.
    - Filtering uses MNE's ``Raw.filter`` and ``Raw.notch_filter``.
    - Unit normalization follows the logic in ``read_data.py``:
      if the signal amplitude is too small (std < 1e-3), it is
      assumed to be in Volts and is converted to microvolts.
    """
    # --------------------------------------------------------------
    # 1. Pick target & reference channels
    # --------------------------------------------------------------
    picks = [ch_name]
    if ref_name:
        picks.append(ref_name)

    # Validate existence
    for p in picks:
        if p not in raw.ch_names:
            return None

    try:
        raw_tmp = raw.copy().pick(picks)
    except Exception:
        return None

    # --------------------------------------------------------------
    # 2. Re-reference channel
    # --------------------------------------------------------------
    if ref_name:
        # Set average reference using the provided reference channel
        raw_tmp.set_eeg_reference([ref_name])
        raw_tmp.pick([ch_name])  # Keep only the target channel

    # --------------------------------------------------------------
    # 3. Filtering (Notch + Bandpass)
    # --------------------------------------------------------------
    if filter_cfg:
        # Notch filter only when sample rate is sufficiently high
        if raw_tmp.info['sfreq'] > 120 and 'notch' in filter_cfg:
            raw_tmp.notch_filter(filter_cfg['notch'], verbose=False)

        if 'bp' in filter_cfg:
            l, h = filter_cfg['bp']
            raw_tmp.filter(l_freq=l, h_freq=h,
                           method='iir', verbose=False)

    # --------------------------------------------------------------
    # 4. Resampling
    # --------------------------------------------------------------
    if int(raw_tmp.info['sfreq']) != target_fs:
        raw_tmp.resample(target_fs, verbose=False)

    # --------------------------------------------------------------
    # 5. Unit Normalization (Volt → µV)
    # --------------------------------------------------------------
    data, _ = raw_tmp[:]

    # If amplitude is extremely small, assume Volt → convert to µV
    if np.std(data) < 1e-3:
        data *= 1e6

    # Return 1D array
    return data[0]
