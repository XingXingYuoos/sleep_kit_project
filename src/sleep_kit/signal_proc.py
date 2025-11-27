"""
sleep_kit.signal_proc
信号处理核心逻辑。
Source: read_data.py loop logic
"""
import numpy as np
import mne

def process_single_channel(raw, ch_name, ref_name=None, target_fs=100, filter_cfg=None):
    """
    对单个通道进行：Pick -> Rereference -> Filter -> Resample -> Unit Fix
    完整保留 read_data.py 中的处理流程。
    """
    # 1. Pick & Rereference
    picks = [ch_name]
    if ref_name:
        picks.append(ref_name)

    # Check if channels exist
    for p in picks:
        if p not in raw.ch_names:
            return None

    try:
        raw_tmp = raw.copy().pick(picks)
    except Exception:
        return None

    if ref_name:
        raw_tmp.set_eeg_reference([ref_name])
        raw_tmp.pick([ch_name]) # Drop ref

    # 2. Filter (Source: read_data.py)
    if filter_cfg:
        # Notch
        if raw_tmp.info['sfreq'] > 120 and 'notch' in filter_cfg:
             raw_tmp.notch_filter(filter_cfg['notch'], verbose=False)
        # Bandpass
        if 'bp' in filter_cfg:
            l, h = filter_cfg['bp']
            raw_tmp.filter(l_freq=l, h_freq=h, method='iir', verbose=False)

    # 3. Resample
    if int(raw_tmp.info['sfreq']) != target_fs:
        raw_tmp.resample(target_fs, verbose=False)

    # 4. Unit Check (Source: read_data.py checkChnValue logic simplified for extraction)
    # Unit: Volt to μV
    data, _ = raw_tmp[:]

    # 原始代码逻辑：if (r._orig_units[c] in ('µV', 'mV')) or (np.std(c_data) < 1e-3): c_data *= 1e6
    # 这里我们使用统计特性判断
    if np.std(data) < 1e-3:
        data *= 1e6

    return data[0] # Return 1D array