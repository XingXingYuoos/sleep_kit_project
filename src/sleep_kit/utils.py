"""
sleep_kit.utils
辅助工具：处理通道名称的匹配与标准化。
"""

def find_str_in_list(expect: str, chList: list):
    """
    Helper function to find a channel name in a list, excluding 'SPO2' false positives.
    Source: read_data.py
    """
    for ch in chList:
        if (expect in ch) and ('SPO2' not in ch):
            return chList.index(ch)
    return None

def get_auto_chn_names(rawChns):
    """
    当没有预设配置表时，尝试自动推断通道名称。
    Source: read_data.py getChnNames()
    """
    # normalized ch names
    rawChns = [s for s in rawChns if 'LEG' not in s]
    rawChns_norm = [''.join(char for char in s if char.isalnum()).upper() for s in rawChns]

    # result
    chnNames = {}
    indRef = True

    # EEG
    for ee in ['F3', 'F4', 'C3', 'C4', 'O1', 'O2']:
        ref_cand = ['M2', 'A2'] if ee[-1] == '3' or ee[-1] == '1' else ['M1', 'A1']
        # with ref first
        index_M = find_str_in_list(ee + ref_cand[0], rawChns_norm)
        index_A = find_str_in_list(ee + ref_cand[1], rawChns_norm)
        if index_M is not None:
            chnNames[ee] = rawChns[index_M]
            indRef = False
        elif index_A is not None:
            chnNames[ee] = rawChns[index_A]
            indRef = False
        else:  # this channel with no ref
            index_EEG = find_str_in_list(ee, rawChns_norm)
            if index_EEG is not None:
                chnNames[ee] = rawChns[index_EEG]
                if indRef:
                    index_A1 = find_str_in_list('A1', rawChns_norm)
                    if index_A1 is not None:
                        chnNames['M2'] = rawChns[index_A1]
                    index_A2 = find_str_in_list('A2', rawChns_norm)
                    if index_A2 is not None:
                        chnNames['M2'] = rawChns[index_A2]
                    index_M1 = find_str_in_list('M1', rawChns_norm)
                    if index_M1 is not None:
                        chnNames['M1'] = rawChns[index_M1]
                    index_M2 = find_str_in_list('M2', rawChns_norm)
                    if index_M2 is not None:
                        chnNames['M2'] = rawChns[index_M2]

    # EOG
    for ee in ['E1', 'E2']:
        ref_cand = ['M', 'A']
        # with ref first
        index_M = find_str_in_list(ee + ref_cand[0], rawChns_norm)
        index_A = find_str_in_list(ee + ref_cand[1], rawChns_norm)
        if index_M is not None:
            chnNames[ee] = rawChns[index_M]
        elif index_A is not None:
            chnNames[ee] = rawChns[index_A]
        else:  # this channel with no ref
            if ee == 'E1':
                default_names = ('E1', 'LOC', 'EOG1', 'EOGL', 'LEOG')
            elif ee == 'E2':
                default_names = ('E2', 'ROC', 'EOG2', 'EOGR', 'REOG')
            else:
                default_names = () # Should not happen

            for name in default_names:
                index_EOG = find_str_in_list(name, rawChns_norm)
                if index_EOG is not None:
                    chnNames[ee] = rawChns[index_EOG]
                    break

    # EMG
    index_EMG = None
    for emg in ('CHIN1', 'LCHIN', 'CHINL', 'CCHIN', 'CHINC', 'CHIN', 'EMG'):  # NOTE: priority
        index_EMG = find_str_in_list(emg, rawChns_norm)
        if index_EMG is not None:
            chnNames['EMG'] = rawChns[index_EMG]
            break

    # try to find EMGref
    if (index_EMG is not None) and rawChns_norm[index_EMG].count('CHIN') < 2 and rawChns_norm[index_EMG].count('EMG') < 2:
        # Avoid modifying the list while iterating logic from original code,
        # but here we just look for another channel
        for emgref in ('CHIN2', 'CHIN3', 'RCHIN', 'CHINR', 'CHIN'):
            index_EMGref = find_str_in_list(emgref, rawChns_norm)
            # Ensure it's not the same channel
            if index_EMGref is not None and index_EMGref != index_EMG:
                chnNames['EMGref'] = rawChns[index_EMGref]
                break

    return chnNames

def get_expected_chn_names(chnNameTable, rawChns):
    """
    根据配置表查找通道。
    Source: read_data.py getExpectedChnNames()
    """
    chnNames = {}
    expect = ['F3', 'F4', 'C3', 'C4', 'O1', 'O2', 'E1', 'E2', 'EMG', 'M1', 'M2', 'EMGref']
    for c in expect:
        found = False
        names = chnNameTable[c] if c in chnNameTable else []
        names = [names] if type(names) is str else list(names)
        names.append(c)  # default channel name
        for name in names:
            for rcn in rawChns:
                if name.upper() == rcn.upper():
                    chnNames[c] = rcn
                    found = True
                    break
            if found: break

    # del exist ref
    for ref in ('M1', 'M2'):
        if ref in chnNames:
            for c in ('F3', 'F4', 'C3', 'C4', 'O1', 'O2', 'E1', 'E2'):
                if (c in chnNames) and (chnNames[ref] in chnNames[c]):
                    del chnNames[ref]
                    break
    # replace alternative channel if ["F4, C4, O2, EMG"] not exist. BUG: replace ref
    if ('F4' not in chnNames) and ('F3' in chnNames):
        chnNames['F4'] = chnNames['F3']
        del chnNames['F3']
    if ('C4' not in chnNames) and ('C3' in chnNames):
        chnNames['C4'] = chnNames['C3']
        del chnNames['C3']
    if ('O2' not in chnNames) and ('O1' in chnNames):
        chnNames['O2'] = chnNames['O1']
        del chnNames['O1']
    if ('EMG' not in chnNames) and ('EMGref' in chnNames):
        chnNames['EMG'] = chnNames['EMGref']
        del chnNames['EMGref']
    return chnNames