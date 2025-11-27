"""
sleep_kit.io
原始数据读取模块 (EDF, H5, MAT)
"""
import mne
import numpy as np
import h5py
from scipy.io import loadmat
from .config import CHANNEL_MAPPING
from .utils import get_expected_chn_names, get_auto_chn_names


def load_h5_as_raw(path):
    """Source: tools/dod_h52raw.py"""
    try:
        f = h5py.File(path, 'r')
        # DOD dataset logic
        if 'dod-o' in str(path) or 'signals' in f:
            # Simplified DOD logic based on uploaded file
            ch_names = ['C3_M2', 'C4_M1', 'F3_M2', 'F4_O2', 'O1_M2', 'O2_M1', 'EOG1', 'EOG2', 'EMG']
            ch_types_mne = ['eeg'] * 6 + ['eog'] * 2 + ['emg']

            # This is a simplified reconstruction.
            # In a real scenario, we iterate keys in f['signals']['eeg'] etc.
            data_list = []
            found_chns = []

            # Try to read standard structure
            for type_grp in ['eeg', 'eog', 'emg']:
                if type_grp in f['signals']:
                    grp = f['signals'][type_grp]
                    for key in grp.keys():
                        data_list.append(grp[key][:])
                        found_chns.append(key)

            if not data_list: return None

            data = np.stack(data_list)
            data *= 1e-6  # uV assumption check

            info = mne.create_info(found_chns, 250, 'eeg')
            custom_raw = mne.io.RawArray(data, info)
            return custom_raw
    except Exception as e:
        print(f"H5 Load Error: {e}")
        return None


def load_mat_as_raw(path):
    """Source: tools/phy_mat2raw.py"""
    try:
        f = loadmat(path)
        if 'val' in f:
            data = f['val']
            # Expecting 8 channels for PHY
            if data.shape[0] > 8: data = data[:8, :]
            data = data.astype(float)
            data *= 1e-6  # unit: μV

            ch_names = ['F3', 'F4', 'C3', 'C4', 'O1', 'O2', 'E1', 'EMG']
            info = mne.create_info(
                ch_names=ch_names,
                ch_types=['eeg'] * 8,
                sfreq=200
            )
            custom_raw = mne.io.RawArray(data, info)
            return custom_raw
    except Exception as e:
        print(f"MAT Load Error: {e}")
        return None


def psg_load_raw(file_path, dataset_name):
    """
    通用加载函数。
    返回: (mne.io.Raw, dict_of_matched_channels)
    """
    file_path = str(file_path)

    # 1. 加载文件
    raw = None
    if file_path.lower().endswith('.edf'):
        try:
            raw = mne.io.read_raw_edf(file_path, preload=True, verbose=False, stim_channel=None)
        except Exception as e:
            print(f"EDF Load Error: {e}")
            return None, {}
    elif file_path.lower().endswith('.h5'):
        raw = load_h5_as_raw(file_path)
    elif file_path.lower().endswith('.mat'):
        raw = load_mat_as_raw(file_path)

    if raw is None:
        return None, {}

    # 2. 获取该数据集的通道映射规则
    mapping_rule = CHANNEL_MAPPING.get(dataset_name)

    # 3. 匹配实际通道名
    if mapping_rule:
        matched_channels = get_expected_chn_names(mapping_rule, raw.ch_names)
    else:
        # 如果没有配置，使用自动推断
        matched_channels = get_auto_chn_names(raw.ch_names)

    return raw, matched_channels