"""
sleep_kit.epoch
切片与序列化。
Source: data_preparation.py
"""
import numpy as np
from sklearn.preprocessing import StandardScaler

def slice_epochs(signal, labels, fs=100, epoch_sec=30):
    """
    将信号 (C, T_total) 和 标签 (N_epochs) 对齐并切片。
    """
    C, L = signal.shape
    samples_per_epoch = int(fs * epoch_sec)
    n_epochs = L // samples_per_epoch

    # 截断信号
    signal = signal[:, :n_epochs * samples_per_epoch]

    # 对齐标签
    if len(labels) < n_epochs:
        n_epochs = len(labels)
        signal = signal[:, :n_epochs * samples_per_epoch]
    elif len(labels) > n_epochs:
        labels = labels[:n_epochs]

    if n_epochs == 0:
        return None, None

    # Reshape: (C, N, T_epoch) -> (N, C, T_epoch)
    epochs_data = signal.reshape(C, n_epochs, samples_per_epoch).transpose(1, 0, 2)
    labels = np.array(labels)

    # 原始代码中的 Unknown 过滤逻辑 (Stage 5)
    # delete ? before and after sleep
    # known_idx = np.where(labels != 5)[0] ...
    # 这里保留全部，让用户在下游清洗，或者你可以取消注释下面的过滤逻辑

    return epochs_data, labels

def standardize_epochs(epochs_data):
    """
    Z-score per subject.
    Source: data_preparation.py
    """
    if epochs_data is None: return None
    N, C, T = epochs_data.shape
    if N == 0: return epochs_data

    # Reshape to (N*T, C)
    data_reshaped = epochs_data.transpose(0, 2, 1).reshape(-1, C)

    scaler = StandardScaler()
    data_scaled = scaler.fit_transform(data_reshaped)

    # Restore
    return data_scaled.reshape(N, T, C).transpose(0, 2, 1)

def package_sequences(epochs, labels, seq_len=20):
    """
    Source: data_preparation.py
    """
    if epochs is None: return None, None
    N = epochs.shape[0]
    n_seq = N // seq_len

    if n_seq == 0: return None, None

    # Trim
    epochs = epochs[:n_seq * seq_len]
    labels = labels[:n_seq * seq_len]

    # Reshape (N_seq, Seq_len, C, T)
    seq_data = epochs.reshape(n_seq, seq_len, epochs.shape[1], epochs.shape[2])
    seq_labels = labels.reshape(n_seq, seq_len)

    return seq_data, seq_labels