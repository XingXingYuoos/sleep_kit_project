"""
sleep_kit.cli
命令行入口。
Source: data_preparation.py logic adapted to CLI
"""
import os
import argparse
import glob
import numpy as np
from tqdm import tqdm

from .config import DATASET_RULES, DEFAULT_PROCESS_CONFIG
from .io import psg_load_raw
from .annotation import load_annotation
from .signal_proc import process_single_channel
from .epoch import slice_epochs, standardize_epochs, package_sequences

def main():
    parser = argparse.ArgumentParser(description="SleepKit PSG Processing")
    parser.add_argument('--dataset', required=True, help="Dataset name in config (e.g., SHHS1)")
    parser.add_argument('--data-root', required=True, help="Path to raw data")
    parser.add_argument('--out-root', required=True, help="Path to output")
    args = parser.parse_args()

    dataset = args.dataset
    data_root = args.data_root
    out_dir = os.path.join(args.out_root, dataset)

    # Setup directories
    os.makedirs(os.path.join(out_dir, 'seq'), exist_ok=True)
    os.makedirs(os.path.join(out_dir, 'label'), exist_ok=True)

    # 1. Config
    rules = DATASET_RULES.get(dataset, DATASET_RULES['SHHS1'])
    config = DEFAULT_PROCESS_CONFIG

    print(f"Dataset: {dataset}")
    print(f"Rules: {rules}")

    # 2. Scan Files
    print("Scanning files...")
    psg_ext = rules['fmt_psg']
    anno_ext = rules['fmt_anno']

    psg_files = sorted(glob.glob(os.path.join(data_root, '**', f'*.{psg_ext}'), recursive=True))
    anno_files = sorted(glob.glob(os.path.join(data_root, '**', f'*.{anno_ext}'), recursive=True))

    print(f"Found {len(psg_files)} PSGs, {len(anno_files)} Annos")

    # Map annos by filename stem
    anno_map = {os.path.splitext(os.path.basename(f))[0]: f for f in anno_files}

    # 3. Main Loop
    for psg_path in tqdm(psg_files):
        try:
            stem = os.path.splitext(os.path.basename(psg_path))[0]

            # Find Anno (Fuzzy Match)
            anno_path = anno_map.get(stem)
            if not anno_path:
                # Try partial match (e.g. shhs1-200001 in shhs1-200001-profusion.xml)
                for k, v in anno_map.items():
                    if stem in k or k in stem:
                        anno_path = v
                        break

            if not anno_path:
                continue

            # Load Raw
            raw, matched_chns = psg_load_raw(psg_path, dataset)
            if not raw: continue

            # Load Anno
            labels = load_annotation(anno_path, rules['reader'])
            if not labels: continue

            # Process Channels
            target_channels = config['channels'] # ['F4', 'E1']
            sigs = []

            for target in target_channels:
                real_name = matched_chns.get(target)
                if not real_name: break

                # Determine Reference
                ref_target = None
                if target in ['F4', 'C4', 'O2']: ref_target = 'M1'
                if target in ['F3', 'C3', 'O1']: ref_target = 'M2'

                real_ref = matched_chns.get(ref_target)

                # Filter selection
                ftype = 'emg' if 'EMG' in target else 'eeg'

                s = process_single_channel(
                    raw, real_name, real_ref,
                    config['sample_rate'],
                    {'bp': config['filter'][ftype], 'notch': config['filter']['notch']}
                )
                if s is not None:
                    sigs.append(s)

            if len(sigs) != len(target_channels):
                continue

            # Stack
            signal_data = np.stack(sigs)

            # Epoch & Standardize
            epochs, l_epochs = slice_epochs(signal_data, labels, config['sample_rate'])
            if epochs is None: continue

            if config['standardize']:
                epochs = standardize_epochs(epochs)

            # Sequence
            seqs, l_seqs = package_sequences(epochs, l_epochs, config['seq_len'])
            if seqs is None: continue

            # Save
            stem_safe = stem.replace('.', '_')
            subj_seq_dir = os.path.join(out_dir, 'seq', stem_safe)
            subj_lbl_dir = os.path.join(out_dir, 'label', stem_safe)
            os.makedirs(subj_seq_dir, exist_ok=True)
            os.makedirs(subj_lbl_dir, exist_ok=True)

            for i in range(len(seqs)):
                np.save(os.path.join(subj_seq_dir, f'{stem_safe}-{i}.npy'), seqs[i].astype(np.float32))
                np.save(os.path.join(subj_lbl_dir, f'{stem_safe}-{i}.npy'), l_seqs[i].astype(np.int64))

        except Exception as e:
            # print(f"Error {psg_path}: {e}")
            pass

if __name__ == '__main__':
    main()