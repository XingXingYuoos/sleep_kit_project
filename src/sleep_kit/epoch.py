"""
sleep_kit.epoch
===============

Epoch slicing, normalization, and sequence packaging utilities.

This module implements the core preprocessing steps used across SleepKit:
1. Cut continuous multichannel PSG signals into fixed-length epochs.
2. Apply per-subject standardization.
3. Package epochs into fixed-length sequences for downstream modeling.

The functions here provide minimal assumptions and are dataset-agnostic.
"""

import numpy as np
from sklearn.preprocessing import StandardScaler


# ----------------------------------------------------------------------
# Epoch slicing
# ----------------------------------------------------------------------

def slice_epochs(signal, labels, fs=100, epoch_sec=30):
    """
    Slice continuous PSG signals into fixed-length epochs.

    Parameters
    ----------
    signal : ndarray, shape (C, T_total)
        Multichannel PSG signal, where C is the number of channels and
        T_total is the number of samples.
    labels : list or ndarray
        List of epoch-level sleep stage labels.
    fs : int, optional
        Sampling rate in Hz. Default is ``100``.
    epoch_sec : int, optional
        Epoch duration in seconds. Default is ``30``.

    Returns
    -------
    epochs_data : ndarray, shape (N, C, T_epoch)
        Sliced epochs, where N is the number of valid epochs.
    labels : ndarray, shape (N,)
        Truncated and aligned labels.
    """
    C, L = signal.shape
    samples_per_epoch = int(fs * epoch_sec)
    n_epochs = L // samples_per_epoch

    # Truncate signal to full epochs
    signal = signal[:, :n_epochs * samples_per_epoch]

    # Align labels
    if len(labels) < n_epochs:
        n_epochs = len(labels)
        signal = signal[:, :n_epochs * samples_per_epoch]
    elif len(labels) > n_epochs:
        labels = labels[:n_epochs]

    if n_epochs == 0:
        return None, None

    # Reshape to (N, C, T_epoch)
    epochs_data = signal.reshape(C, n_epochs, samples_per_epoch).transpose(1, 0, 2)
    labels = np.array(labels)

    # Note: Unknown stage (5) filtering is intentionally omitted for flexibility.
    return epochs_data, labels


# ----------------------------------------------------------------------
# Per-subject standardization
# ----------------------------------------------------------------------

def standardize_epochs(epochs_data):
    """
    Apply per-subject Z-score normalization across all epochs.

    Parameters
    ----------
    epochs_data : ndarray, shape (N, C, T)
        Epoch data to be standardized.

    Returns
    -------
    ndarray
        Standardized epoch data with the same shape.

    Notes
    -----
    - Standardization is applied across all epochs and time samples for each
      channel independently.
    - Transformation: (value - mean) / std
    """
    if epochs_data is None:
        return None

    N, C, T = epochs_data.shape
    if N == 0:
        return epochs_data

    # Reshape to (N*T, C)
    data_reshaped = epochs_data.transpose(0, 2, 1).reshape(-1, C)

    scaler = StandardScaler()
    data_scaled = scaler.fit_transform(data_reshaped)

    # Restore original shape
    return data_scaled.reshape(N, T, C).transpose(0, 2, 1)


# ----------------------------------------------------------------------
# Sequence packaging
# ----------------------------------------------------------------------

def package_sequences(epochs, labels, seq_len=20):
    """
    Group epochs into fixed-length sequences.

    Parameters
    ----------
    epochs : ndarray, shape (N, C, T)
        Epoch-level data.
    labels : ndarray, shape (N,)
        Corresponding epoch labels.
    seq_len : int, optional
        Number of epochs per sequence. Default is ``20``.

    Returns
    -------
    seq_data : ndarray, shape (N_seq, seq_len, C, T)
        Packaged epoch sequences.
    seq_labels : ndarray, shape (N_seq, seq_len)
        Corresponding label sequences.

    Notes
    -----
    - Sequences shorter than ``seq_len`` are discarded.
    - The function performs simple truncation rather than sliding windows.
    """
    if epochs is None:
        return None, None

    N = epochs.shape[0]
    n_seq = N // seq_len

    if n_seq == 0:
        return None, None

    # Truncate to full sequences
    epochs = epochs[:n_seq * seq_len]
    labels = labels[:n_seq * seq_len]

    seq_data = epochs.reshape(n_seq, seq_len, epochs.shape[1], epochs.shape[2])
    seq_labels = labels.reshape(n_seq, seq_len)

    return seq_data, seq_labels
