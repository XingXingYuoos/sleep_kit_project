"""
sleep_kit.config
================

Centralized configuration module for SleepKit.

This module stores dataset-specific channel mapping rules,
file-format definitions, annotation readers, and default
preprocessing settings. It acts as the unified configuration
backend for all data-loading and preprocessing utilities.

Contents
--------
1. CHANNEL_MAPPING : dict
    Defines per-dataset channel aliasing and naming variations.
2. DATASET_RULES : dict
    Defines PSG file formats, annotation formats, and corresponding
    reader functions for each dataset.
3. DEFAULT_PROCESS_CONFIG : dict
    Default preprocessing parameters used across SleepKit.

Notes
-----
- CHANNEL_MAPPING resolves channel-name inconsistencies across
  heterogeneous PSG datasets.
- DATASET_RULES binds datasets to annotation readers implemented
  in ``sleep_kit.annotation``.
- DEFAULT_PROCESS_CONFIG is used by both the API and CLI interfaces.
"""

# ==============================================================================
# 1. CHANNEL MAPPING
# ==============================================================================
# These mappings unify heterogeneous channel naming conventions across datasets.
# Each key corresponds to a dataset, and each value defines its channel aliases.
CHANNEL_MAPPING = {
    'SHHS1': {'C4': 'EEG',
              'C3': ('EEG(sec)', 'EEG2', 'EEG 2', 'EEG(SEC)', 'EEG sec'),
              'E1': 'EOG(L)', 'E2': 'EOG(R)'},

    'SHHS2': {'C4': 'EEG',
              'C3': ('EEG(sec)', 'EEG2'),
              'E1': 'EOG(L)', 'E2': 'EOG(R)'},

    'CCSHS': {'E1': 'LOC', 'E2': 'ROC', 'M1': 'A1', 'M2': 'A2',
              'EMG': 'EMG1', 'EMGref': 'EMG2'},

    'SOF': {'E1': 'LOC', 'E2': 'ROC', 'M1': 'A1', 'M2': 'A2',
            'EMG': ('L Chin', 'EMG/L'),
            'EMGref': ('R Chin', 'EMG/R')},

    'CFS': {'E1': 'LOC', 'E2': 'ROC', 'EMG': 'EMG2', 'EMGref': 'EMG1'},

    'MROS1': {'C4': 'C4-A1', 'C3': 'C3-A2',
              'E1': 'LOC', 'E2': 'ROC', 'M1': 'A1', 'M2': 'A2',
              'EMG': ('LChin', 'L Chin', 'L Chin-R Chin'),
              'EMGref': ('RChin', 'R Chin')},

    'MROS2': {'C4': 'C4-A1', 'C3': 'C3-A2',
              'E1': 'LOC', 'E2': 'ROC', 'M1': 'A1', 'M2': 'A2',
              'EMG': ('LChin', 'L Chin', 'L Chin-R Chin'),
              'EMGref': ('RChin', 'R Chin')},

    'MESA': {'F4': 'EEG1', 'C4': 'EEG3', 'O2': 'EEG2',
             'E1': 'EOG-L', 'E2': 'EOG-R'},

    'HPAP1': {'C3': 'C3-M2', 'C4': 'C4-M1',
              'E1': ('E1-M2', 'E-1', 'L-EOG', 'LOC', 'E1-E2'),
              'E2': ('E2-M1', 'E-2', 'R-EOG', 'ROC'),
              'M2': 'E2-M1',
              'EMG': ('LCHIN', 'CHIN', 'CHIN1-CHIN2', 'Lchin-Cchin',
                      'EMG1', 'L.', 'Chin1', 'Chin EMG'),
              'EMGref': ('CCHIN', 'RCHIN', 'EMG2', 'C.', 'Chin2')},

    'HPAP2': {'C3': 'C3-M2', 'C4': 'C4-M1',
              'E1': ('E1-M2', 'E-1', 'L-EOG', 'LOC', 'E1-E2'),
              'E2': ('E2-M1', 'E-2', 'R-EOG', 'ROC'),
              'M2': 'E2-M1',
              'EMG': ('LCHIN', 'CHIN', 'CHIN1-CHIN2', 'Lchin-Cchin',
                      'EMG1', 'L.', 'Chin1', 'Chin EMG'),
              'EMGref': ('CCHIN', 'RCHIN', 'EMG2', 'C.', 'Chin2')},

    'ABC': {'EMG': 'Chin2', 'EMGref': 'Chin1'},

    'NCHSDB': {'F3': ('EEG F3-M2', 'EEG F3'),
               'F4': ('EEG F4-M1', 'EEG F4'),
               'C3': ('EEG C3-M2', 'EEG C3'),
               'C4': ('EEG C4-M1', 'EEG C4'),
               'O1': ('EEG O1-M2', 'EEG O1'),
               'O2': ('EEG O2-M1', 'EEG O2'),
               'E1': ('EOG LOC-M2', 'LOC', 'EEG E1'),
               'E2': ('EOG ROC-M1', 'ROC', 'EEG E2'),
               'EMG': ('EMG Chin1-Chin2', 'EMG Chin2-Chin1',
                       'EMG Chin1-Chin3', 'EMG Chin3-Chin2',
                       'EEG Chin1-Chin2', 'Chin1', 'EEG Chin1'),
               'EMGref': ('Chin2', 'EEG Chin2')},

    'HMC': {'F4': 'EEG F4-M1', 'C4': 'EEG C4-M1', 'O2': 'EEG O2-M1',
            'C3': 'EEG C3-M2', 'EMG': 'EMG chin',
            'E1': 'EOG E1-M2', 'E2': 'EOG E2-M2'},

    # MNC sub-datasets
    'SSC': {'EMG': ('cchin_l', 'chin', 'cchin'),
            'EMGref': ('rchin_c', 'lchin')},
    'CNC': {'EMG': ('cchin_l', 'chin', 'cchin'),
            'EMGref': ('rchin_c', 'lchin')},
    'DHC': {'EMG': ('cchin_l', 'chin', 'cchin'),
            'EMGref': ('rchin_c', 'lchin')},

    'DCSM': {'F3': 'F3-M2', 'F4': 'F4-M1',
             'C3': 'C3-M2', 'C4': 'C4-M1',
             'O1': 'O1-M2', 'O2': 'O2-M1',
             'E1': 'E1-M2', 'E2': 'E2-M2', 'EMG': 'CHIN'},

    'DOD': {'channels': 'never mind'},
    'PHY': {'channels': 'never mind'},

    'MASS13': {'F3': ('EEG F3-CLE', 'EEG F3-LER'),
               'F4': ('EEG F4-CLE', 'EEG F4-LER'),
               'C3': ('EEG C3-CLE', 'EEG C3-LER'),
               'C4': ('EEG C4-CLE', 'EEG C4-LER'),
               'O1': ('EEG O1-CLE', 'EEG O1-LER'),
               'O2': ('EEG O2-CLE', 'EEG O2-LER'),
               'E1': 'EOG Left Horiz',
               'E2': 'EOG Right Horiz',
               'M1': 'EEG A1-CLE',
               'M2': 'EEG A2-CLE',
               'EMG': 'EMG Chin1',
               'EMGref': 'EMG Chin2'},

    'STAGES': None,

    'WSC': {'F3': ('F3_M2', 'F3_M1', 'F3_AVG'),
            'C3': ('C3_M2', 'C3_M1'),
            'O1': ('O1_M2', 'O1_M1', 'O1_AVG'),
            'F4': 'F4_M1',
            'C4': ('C4_M1', 'C4_AVG'),
            'O2': 'O2_M1',
            'EMG': ('chin', 'cchin_l', 'rchin_l'),
            'EMGref': 'cchin_r'},

    'ISRC': {'C3': 'C3-A2', 'C4': ('C4-A1', 'C4-A2'),
             'O1': 'O1-A2', 'O2': ('O2-A1', 'O2-A2'),
             'E1': 'LOC-A2', 'E2': ('ROC-A1', 'ROC-A2'),
             'EMG': 'EMG1-EMG2'}
}

# ==============================================================================
# 2. DATASET RULES
# ==============================================================================
# Defines raw PSG file format, annotation format, and the annotation reader name.
DATASET_RULES = {
    'SHHS1':  {'fmt_psg': 'edf', 'fmt_anno': 'xml', 'reader': 'xml'},
    'SHHS2':  {'fmt_psg': 'edf', 'fmt_anno': 'xml', 'reader': 'xml'},
    'CCSHS':  {'fmt_psg': 'edf', 'fmt_anno': 'xml', 'reader': 'xml'},
    'SOF':    {'fmt_psg': 'edf', 'fmt_anno': 'xml', 'reader': 'xml'},
    'CFS':    {'fmt_psg': 'edf', 'fmt_anno': 'xml', 'reader': 'xml'},
    'MROS1':  {'fmt_psg': 'edf', 'fmt_anno': 'xml', 'reader': 'xml'},
    'MROS2':  {'fmt_psg': 'edf', 'fmt_anno': 'xml', 'reader': 'xml'},
    'MESA':   {'fmt_psg': 'edf', 'fmt_anno': 'xml', 'reader': 'xml'},
    'HPAP1':  {'fmt_psg': 'edf', 'fmt_anno': 'xml', 'reader': 'xml'},
    'HPAP2':  {'fmt_psg': 'edf', 'fmt_anno': 'xml', 'reader': 'xml'},

    'STAGES': {'fmt_psg': 'edf', 'fmt_anno': 'csv', 'reader': 'stages_csv'},
    'MASS13': {'fmt_psg': 'edf', 'fmt_anno': 'txt', 'reader': 'mass_txt'},

    'HMC':    {'fmt_psg': 'edf', 'fmt_anno': 'txt', 'reader': 'hmc_txt'},

    'MNC':    {'fmt_psg': 'edf', 'fmt_anno': 'eannot', 'reader': 'eannot'},
    'SSC':    {'fmt_psg': 'edf', 'fmt_anno': 'eannot', 'reader': 'eannot'},
    'DHC':    {'fmt_psg': 'edf', 'fmt_anno': 'eannot', 'reader': 'eannot'},
    'CNC':    {'fmt_psg': 'edf', 'fmt_anno': 'eannot', 'reader': 'eannot'},

    'ABC':    {'fmt_psg': 'edf', 'fmt_anno': 'xml', 'reader': 'xml'},

    'NCHSDB': {'fmt_psg': 'edf', 'fmt_anno': 'tsv', 'reader': 'tsv'},

    'PHY':    {'fmt_psg': 'mat', 'fmt_anno': 'mat', 'reader': 'phy_mat'},

    'DCSM':   {'fmt_psg': 'edf', 'fmt_anno': 'ids', 'reader': 'dcsm_ids'},

    'DOD':    {'fmt_psg': 'h5',  'fmt_anno': 'h5', 'reader': 'h5'},

    'WSC':    {'fmt_psg': 'edf', 'fmt_anno': 'txt', 'reader': 'wsc_txt'},

    'ISRC':   {'fmt_psg': 'edf', 'fmt_anno': 'STA', 'reader': None},

    'HomePAP':{'fmt_psg': 'edf', 'fmt_anno': 'xml', 'reader': 'xml'},
}

# ==============================================================================
# 3. DEFAULT PROCESSING CONFIG
# ==============================================================================
DEFAULT_PROCESS_CONFIG = {
    'sample_rate': 100,
    'epoch_sec': 30,
    'seq_len': 20,
    'channels': ['F4', 'E1'],
    'filter': {
        'eeg': [0.3, 35],
        'emg': [10, 49],
        'notch': [50, 60]
    },
    'standardize': True
}
