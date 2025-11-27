"""
sleep_kit.io
============

Raw PSG data loading utilities (EDF, H5, MAT).

This module unifies the loading of heterogeneous PSG file formats into
a consistent ``mne.io.Raw`` object. It supports:

- Standard EDF (MNE-backed)
- HDF5-based PSG variants (e.g., DOD dataset)
- MATLAB ``.mat`` PSG dumps (e.g., PHY dataset)

The returned object is always:
    (raw: mne.io.Raw, matched_channels: dict)

Notes
-----
- Channel name normalization is handled via ``CHANNEL_MAPPING`` defined
  in ``sleep_kit.config``.
- If a dataset is not explicitly mapped, automatic channel inference
  is performed through ``get_auto_chn_names``.
"""

import mne
import numpy as np
import h5py
from scipy.io import loadmat

from .config import CHANNEL_MAPPING
from .utils import get_expected_chn_names, get_auto_chn_names


# ----------------------------------------------------------------------
# 1. HDF5 Loader (DOD-like structure)
# ----------------------------------------------------------------------

def load_h5_as_raw(path):
    """
    Load PSG data from an HDF5 file into an ``mne.io.Raw`` object.

    Parameters
    ----------
    path : str
        Path to the ``.h5`` file.

    Returns
    -------
    raw : mne.io.Raw or None
        Loaded signal. Returns None if loading fails or if file structure
        does not match expected DOD-style layout.

    Notes
    -----
    - This loader supports a simplified subset of the DOD dataset format.
    - Expected structure:
        f['signals']['eeg'][...]
        f['signals']['eog'][...]
        f['signals']['emg'][...]
    - Amplitude is assumed to be in microvolts (converted to volts).
    """
    try:
        f = h5py.File(path, 'r')

        if 'dod-o' in str(path) or 'signals' in f:
            data_list = []
            found_chns = []

            for type_grp in ['eeg', 'eog', 'emg']:
                if type_grp in f['signals']:
                    grp = f['signals'][type_grp]
                    for key in grp.keys():
                        data_list.append(grp[key][:])
                        found_chns.append(key)

            if not data_list:
                return None

            data = np.stack(data_list)
            data *= 1e-6  # Convert µV → V

            info = mne.create_info(found_chns, sfreq=250, ch_types='eeg')
            raw = mne.io.RawArray(data, info)
            return raw

    except Exception as e:
        print(f"H5 Load Error: {e}")

    return None


# ----------------------------------------------------------------------
# 2. MAT Loader (PHY-like structure)
# ----------------------------------------------------------------------

def load_mat_as_raw(path):
    """
    Load PSG data from MATLAB ``.mat`` file into an ``mne.io.Raw`` object.

    Parameters
    ----------
    path : str
        Path to the ``.mat`` file.

    Returns
    -------
    raw : mne.io.Raw or None
        Standardized MNE Raw object if loading succeeds.

    Notes
    -----
    - Supports PHY v7.3 MAT dumps where signals are stored in ``val``.
    - Assumes eight channels in fixed order:
        F3, F4, C3, C4, O1, O2, E1, EMG
    - Assumes sampling rate = 200 Hz.
    """
    try:
        f = loadmat(path)

        if 'val' in f:
            data = f['val']

            # Limit to the first 8 channels if more are present
            if data.shape[0] > 8:
                data = data[:8, :]

            data = data.astype(float)
            data *= 1e-6  # Convert µV → V

            ch_names = ['F3', 'F4', 'C3', 'C4', 'O1', 'O2', 'E1', 'EMG']
            info = mne.create_info(
                ch_names=ch_names,
                ch_types=['eeg'] * 8,
                sfreq=200
            )
            raw = mne.io.RawArray(data, info)
            return raw

    except Exception as e:
        print(f"MAT Load Error: {e}")

    return None


# ----------------------------------------------------------------------
# 3. Universal Loader (EDF/H5/MAT)
# ----------------------------------------------------------------------

def psg_load_raw(file_path, dataset_name):
    """
    Load raw PSG signal and match channel names.

    Parameters
    ----------
    file_path : str
        Path to the raw PSG file (.edf, .h5, .mat).
    dataset_name : str
        Name of the dataset whose channel mapping rules should be used.

    Returns
    -------
    raw : mne.io.Raw or None
        Loaded raw signal. None if file unsupported or loading fails.
    matched_channels : dict
        Mapping from SleepKit expected channel names to actual channel names
        found in the file.

    Notes
    -----
    - EDF files are loaded via ``mne.io.read_raw_edf``.
    - HDF5 files use ``load_h5_as_raw``.
    - MAT files use ``load_mat_as_raw``.
    - CHANNEL_MAPPING provides dataset-specific canonical names.
    - If no mapping exists for a dataset, channel names are inferred
      automatically via ``get_auto_chn_names``.
    """
    file_path = str(file_path)
    raw = None

    # --------------------------------------------------------------
    # Load file by extension
    # --------------------------------------------------------------
    if file_path.lower().endswith('.edf'):
        try:
            raw = mne.io.read_raw_edf(
                file_path, preload=True, verbose=False, stim_channel=None
            )
        except Exception as e:
            print(f"EDF Load Error: {e}")
            return None, {}

    elif file_path.lower().endswith('.h5'):
        raw = load_h5_as_raw(file_path)

    elif file_path.lower().endswith('.mat'):
        raw = load_mat_as_raw(file_path)

    if raw is None:
        return None, {}

    # --------------------------------------------------------------
    # Apply dataset-specific channel mapping
    # --------------------------------------------------------------
    mapping_rule = CHANNEL_MAPPING.get(dataset_name)

    if mapping_rule:
        matched_channels = get_expected_chn_names(mapping_rule, raw.ch_names)
    else:
        matched_channels = get_auto_chn_names(raw.ch_names)

    return raw, matched_channels
