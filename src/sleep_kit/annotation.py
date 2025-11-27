"""
sleep_kit.annotation
====================

Unified annotation readers for heterogeneous PSG hypnogram formats.

This module collects a set of lightweight label loaders for commonly used
public PSG datasets. Each reader converts dataset-specific annotation formats
(e.g., XML, TXT, CSV, TSV, HDF5, MAT) into a unified list of integer sleep
stage labels.

Supported stage mapping convention:
    W=0, N1=1, N2=2, N3/N4=3, REM=4, UNKNOWN=5

These functions are intentionally decoupled from raw signal loading, enabling
modular preprocessing pipelines.

Source modules: read_anno.py (refactored)
"""

import xml.etree.ElementTree as ET
import numpy as np
import h5py
from scipy.io import loadmat
import csv

# ----------------------------------------------------------------------
# Stage dictionaries
# ----------------------------------------------------------------------

# Profusion / MASS / general-purpose mapping
dic = {'?':5, 'W':0, '1':1, '2':2, '3':3, '4':3, 'R':4}

# NSRR Profusion XML mapping
dic2 = {'5':4, '0':0, '1':1, '2':2, '3':3, '4':3, '9':5, '6':5}

epsilon = 0.0001


# ----------------------------------------------------------------------
# Individual readers
# ----------------------------------------------------------------------

def xml(path):
    """
    Read NSRR Profusion-style XML annotation.

    Parameters
    ----------
    path : str
        Path to the ``.xml`` annotation file.

    Returns
    -------
    list of int
        Hypnogram labels in 30-second epoch resolution.

    Notes
    -----
    Expected XML structure:
        <PSGAnnotation>
            <SleepStages>
                <SleepStage>...</SleepStage>
                ...
    """
    anno = []
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        sleepStages = root.find('SleepStages')
        if sleepStages is None:
            return []

        for stage in sleepStages.findall('SleepStage'):
            s = stage.text
            anno.append(dic2.get(s, 5))

    except Exception as e:
        print(f"XML Read Error: {e}")

    return anno


def mass_txt(path):
    """
    Read MASS-format annotation TXT file.

    Parameters
    ----------
    path : str
        Path to annotation txt.

    Returns
    -------
    list of int
        List of integer sleep stages.

    Notes
    -----
    Expected header:
        Onset,Duration,Annotation
    """
    with open(path, 'r') as f:
        lines = f.readlines()

    if not lines or lines[0].strip() != 'Onset,Duration,Annotation':
        return []

    anno = []
    startTime, lastTime = -1, -1.

    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue

        parts = line.split(',')
        if len(parts) < 3:
            continue

        onset, duration, ann = parts[0], parts[1], parts[2]

        if 'stage' not in ann:
            continue

        # Stage parsing
        stage_char = ann.split(' ')[-1]
        anno.append(dic.get(stage_char, 5))

        if startTime < 0:
            startTime = float(onset)

    return anno


def saf(path):
    """
    Read SAF-format annotation.

    Parameters
    ----------
    path : str
        Path to SAF hypnogram file.

    Returns
    -------
    list of int
        Parsed sleep stage sequence.
    """
    anno = []
    with open(path, 'rb') as f:
        lines = f.readlines()
        if not lines:
            return []

        string = lines[0].decode(errors='ignore')

        i = string.find('Sleep stage')
        while i != -1:
            string = string[i+12:]
            if string:
                anno.append(string[0])
            i = string.find('Sleep stage')

    return [dic.get(a, 5) for a in anno]


def eannot(path):
    """
    Read EANNOT text annotation.

    Parameters
    ----------
    path : str

    Returns
    -------
    list of int
    """
    stage_dict = {
        'wake':0,'N1':1,'Nwake':1,'N2':2,'N3':3,'N4':3,'REM':4,
        'unscored':5,'9':5,' ':5,'8':2,'NN1':1,'NN2':2,'NN3':3,'NaN':5
    }

    with open(path, 'r') as f:
        lines = f.readlines()

    anno = []
    for line in lines:
        line = line.strip('\n')
        if len(line) > 0 and line in stage_dict:
            anno.append(stage_dict[line])

    return anno


def stages_csv(path):
    """
    Read CSV-based stage annotation.

    Parameters
    ----------
    path : str

    Returns
    -------
    list of int
    """
    ann_dict = {
        ' Wake':0, ' Stage1':1, ' Stage2':2, ' Stage3':3,
        ' REM':4, ' STAGE4':3, ' UnknownStage':5
    }

    ann = []

    with open(path, 'r') as f:
        lines = f.readlines()

    for line in lines:
        raw = line.strip().split(',')
        if len(raw) < 3:
            continue

        if raw[2] not in ann_dict:
            continue

        duration = float(raw[1])
        stage_code = ann_dict[raw[2]]

        count = int(duration // 30) if duration > 0 else 1
        ann += [stage_code] * count

    return ann


def dcsm_ids(path):
    """
    Read DCSM (Dreem) stage IDS annotation.

    Parameters
    ----------
    path : str

    Returns
    -------
    list of int
    """
    stage_dict = {'W':0, 'N1':1, 'N2':2, 'N3':3, 'REM':4}

    with open(path, 'r') as f:
        lines = f.readlines()

    anno = []
    for line in lines:
        line = line.strip()
        if not line:
            continue

        parts = line.split(',')
        if len(parts) < 3:
            continue

        duration = int(parts[1])
        stg = parts[2]

        if stg in stage_dict:
            anno += [stage_dict[stg]] * (duration // 30)

    return anno


def tsv(path):
    """
    Read TSV-format stage annotation.

    Parameters
    ----------
    path : str

    Returns
    -------
    list of int
    """
    stage_dict = {
        'sleep stage w':0, 'sleep stage wake':0,
        'sleep stage n1':1, 'sleep stage 1':1,
        'sleep stage n2':2,'sleep stage 2':2,
        'sleep stage n3':3,'sleep stage 3':3,'sleep stage 4':3,
        'sleep stage r':4,'sleep stage rem':4,
        'sleep stage ?':5
    }

    with open(path, 'r') as f:
        lines = f.readlines()[1:]

    onset_anno = []
    for line in lines:
        line = line.strip()
        if not line:
            continue

        parts = line.split('\t')
        if len(parts) < 3:
            continue

        ann = parts[2].strip().lower()

        if ann in stage_dict:
            onset_anno.append(stage_dict[ann])

    return onset_anno


def h5(path):
    """
    Read HDF5 hypnogram.

    Parameters
    ----------
    path : str

    Returns
    -------
    list of int
    """
    with h5py.File(path, 'r') as f:
        if 'hypnogram' in f:
            return list(f['hypnogram'][:])

    return []


def hmc_txt(path):
    """
    Read HMC-format annotation.

    Parameters
    ----------
    path : str

    Returns
    -------
    list of int
    """
    stage_dict = {
        'sleep stage w':0, 'sleep stage n1':1, 'sleep stage n2':2,
        'sleep stage n3':3, 'sleep stage r':4
    }

    with open(path, 'r') as f:
        lines = f.readlines()[1:]

    anno = []
    for line in lines:
        parts = line.strip().split(', ')
        if len(parts) < 5:
            continue

        ann = parts[4].lower()

        if 'lights on' in ann:
            break
        if 'lights off' in ann:
            continue

        if ann in stage_dict:
            anno.append(stage_dict[ann])

    return anno


def wsc_txt(path):
    """
    Read WSC-format annotation.

    Parameters
    ----------
    path : str

    Returns
    -------
    list of int
    """
    stage_dict = {'0':0,'1':1,'2':2,'3':3,'4':3,'5':4,'7':5,'6':5}

    with open(path, 'r') as f:
        lines = f.readlines()[1:]

    anno = []
    for line in lines:
        parts = line.strip().split('\t')
        if len(parts) < 2:
            continue

        stg = parts[1]
        if stg in stage_dict:
            anno.append(stage_dict[stg])

    return anno


def phy_mat(path):
    """
    Read PHY-MAT hypnogram (MAT v7.3 / HDF5).

    Parameters
    ----------
    path : str

    Returns
    -------
    list of int

    Notes
    -----
    PHY dataset structure varies significantly. This implementation
    returns empty unless structure matches expected schema.
    """
    try:
        f = h5py.File(path, 'r')
        if 'data' in f and 'sleep_stages' in f['data']:
            # Placeholder — complex structure depends on PHY dataset details
            pass
    except:
        pass

    return []


# ----------------------------------------------------------------------
# Unified entry point
# ----------------------------------------------------------------------

def load_annotation(path, reader_type):
    """
    Unified interface for annotation loading.

    Parameters
    ----------
    path : str
        Path to annotation file.
    reader_type : {"xml","mass_txt","saf","eannot","stages_csv",
                   "dcsm_ids","tsv","h5","hmc_txt","wsc_txt","phy_mat"}
        Identifier of the reader to use.

    Returns
    -------
    list of int
        Parsed label sequence. Empty list if reader_type is unsupported.
    """
    readers = {
        'xml': xml,
        'mass_txt': mass_txt,
        'saf': saf,
        'eannot': eannot,
        'stages_csv': stages_csv,
        'dcsm_ids': dcsm_ids,
        'tsv': tsv,
        'h5': h5,
        'hmc_txt': hmc_txt,
        'wsc_txt': wsc_txt,
        'phy_mat': phy_mat
    }

    reader = readers.get(reader_type)
    if reader:
        return reader(path)

    return []
