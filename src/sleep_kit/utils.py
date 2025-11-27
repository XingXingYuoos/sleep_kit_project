"""
sleep_kit.utils
===============

Utility helpers for channel-name normalization and matching.

This module provides robust channel-name inference utilities designed
for heterogeneous PSG datasets where channel naming conventions vary
significantly across centers. It supports:

- Exact-matching against dataset-specific channel tables
- Automatic channel inference (when no mapping table is provided)
- Flexible, substring-based matching while excluding false positives
"""

# ----------------------------------------------------------------------
# Helper: substring channel search
# ----------------------------------------------------------------------

def find_str_in_list(expect: str, ch_list: list):
    """
    Find the index of a channel name that contains the expected substring.

    Parameters
    ----------
    expect : str
        Expected substring (case-insensitive).
    ch_list : list of str
        List of normalized or raw channel names.

    Returns
    -------
    int or None
        Index of the matching channel, or None if not found.

    Notes
    -----
    - Channels containing 'SPO2' are ignored to avoid false positive matches.
    - Used heavily by automatic channel inference logic.
    """
    for idx, ch in enumerate(ch_list):
        if (expect in ch) and ('SPO2' not in ch):
            return idx
    return None


# ----------------------------------------------------------------------
# Automatic channel inference (fallback)
# ----------------------------------------------------------------------

def get_auto_chn_names(rawChns):
    """
    Automatically infer canonical channel names when no mapping table is provided.

    Parameters
    ----------
    rawChns : list of str
        Raw channel names as found in the PSG file.

    Returns
    -------
    dict
        Dictionary mapping canonical names:
        {'F3','F4','C3','C4','O1','O2','E1','E2','EMG','EMGref',...}
        to their matched raw channel names.

    Notes
    -----
    - This method normalizes channel names by removing non-alphanumeric characters
      and converting to uppercase.
    - Reference channels (M1/M2/A1/A2) are inferred heuristically.
    - Logic is adapted directly from original ``read_data.py``.
    """
    # Remove leg channels
    rawChns = [s for s in rawChns if 'LEG' not in s]

    # Normalize (remove non-alphanumeric)
    raw_norm = [''.join(char for char in s if char.isalnum()).upper() for s in rawChns]

    chnNames = {}
    indRef = True

    # --------------------------------------------------------------
    # EEG channels (F3/F4/C3/C4/O1/O2)
    # --------------------------------------------------------------
    for ee in ['F3', 'F4', 'C3', 'C4', 'O1', 'O2']:
        ref_cand = ['M2', 'A2'] if ee[-1] in ('3', '1') else ['M1', 'A1']

        index_M = find_str_in_list(ee + ref_cand[0], raw_norm)
        index_A = find_str_in_list(ee + ref_cand[1], raw_norm)

        if index_M is not None:
            chnNames[ee] = rawChns[index_M]
            indRef = False
        elif index_A is not None:
            chnNames[ee] = rawChns[index_A]
            indRef = False
        else:
            index_EEG = find_str_in_list(ee, raw_norm)
            if index_EEG is not None:
                chnNames[ee] = rawChns[index_EEG]

                if indRef:
                    # Infer reference channels
                    for suffix in ['A1', 'A2', 'M1', 'M2']:
                        idx = find_str_in_list(suffix, raw_norm)
                        if idx is not None:
                            chnNames.setdefault('M2', rawChns[idx])

    # --------------------------------------------------------------
    # EOG channels (E1/E2)
    # --------------------------------------------------------------
    for ee in ['E1', 'E2']:
        index_M = find_str_in_list(ee + 'M', raw_norm)
        index_A = find_str_in_list(ee + 'A', raw_norm)

        if index_M is not None:
            chnNames[ee] = rawChns[index_M]
            continue
        if index_A is not None:
            chnNames[ee] = rawChns[index_A]
            continue

        defaults = {
            'E1': ('E1', 'LOC', 'EOG1', 'EOGL', 'LEOG'),
            'E2': ('E2', 'ROC', 'EOG2', 'EOGR', 'REOG')
        }
        for name in defaults.get(ee, []):
            index_EOG = find_str_in_list(name, raw_norm)
            if index_EOG is not None:
                chnNames[ee] = rawChns[index_EOG]
                break

    # --------------------------------------------------------------
    # EMG channels
    # --------------------------------------------------------------
    index_EMG = None
    for emg in ('CHIN1', 'LCHIN', 'CHINL', 'CCHIN', 'CHINC', 'CHIN', 'EMG'):
        idx = find_str_in_list(emg, raw_norm)
        if idx is not None:
            chnNames['EMG'] = rawChns[idx]
            index_EMG = idx
            break

    # EMG reference detection
    if (index_EMG is not None and
        raw_norm[index_EMG].count('CHIN') < 2 and
        raw_norm[index_EMG].count('EMG') < 2):

        for emgref in ('CHIN2', 'CHIN3', 'RCHIN', 'CHINR', 'CHIN'):
            idx = find_str_in_list(emgref, raw_norm)
            if idx is not None and idx != index_EMG:
                chnNames['EMGref'] = rawChns[idx]
                break

    return chnNames


# ----------------------------------------------------------------------
# Expected-channel lookup via configuration table
# ----------------------------------------------------------------------

def get_expected_chn_names(chnNameTable, rawChns):
    """
    Retrieve canonical channel mapping from a configuration table.

    Parameters
    ----------
    chnNameTable : dict
        Per-dataset mapping rule (from config).
    rawChns : list of str
        Raw channel names found in the PSG file.

    Returns
    -------
    dict
        Dictionary of canonical → matched raw name.

    Notes
    -----
    - Performs case-insensitive matching.
    - Applies fallback substitution (e.g., F3 → F4) if expected channels
      are missing.
    - Logic faithfully follows ``read_data.py`` to maintain compatibility.
    """
    chnNames = {}
    expected = ['F3', 'F4', 'C3', 'C4', 'O1', 'O2',
                'E1', 'E2', 'EMG', 'M1', 'M2', 'EMGref']

    for c in expected:
        found = False

        names = chnNameTable[c] if c in chnNameTable else []
        names = [names] if isinstance(names, str) else list(names)
        names.append(c)  # default

        for name in names:
            for rcn in rawChns:
                if name.upper() == rcn.upper():
                    chnNames[c] = rcn
                    found = True
                    break
            if found:
                break

    # Remove incorrect references
    for ref in ('M1', 'M2'):
        if ref in chnNames:
            for c in ('F3', 'F4', 'C3', 'C4', 'O1', 'O2', 'E1', 'E2'):
                if c in chnNames and chnNames[ref] in chnNames[c]:
                    del chnNames[ref]
                    break

    # Fallback replacement rules
    if 'F4' not in chnNames and 'F3' in chnNames:
        chnNames['F4'] = chnNames.pop('F3')
    if 'C4' not in chnNames and 'C3' in chnNames:
        chnNames['C4'] = chnNames.pop('C3')
    if 'O2' not in chnNames and 'O1' in chnNames:
        chnNames['O2'] = chnNames.pop('O1')
    if 'EMG' not in chnNames and 'EMGref' in chnNames:
        chnNames['EMG'] = chnNames.pop('EMGref')

    return chnNames
