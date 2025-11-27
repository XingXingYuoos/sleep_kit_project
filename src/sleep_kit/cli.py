"""
sleep_kit.cli
=============

Command-line interface for SleepKit PSG preprocessing.

This module provides a minimal CLI that exposes the core PSG-to-Numpy
conversion pipeline. It performs dataset scanning, raw PSG loading,
channel selection, filtering, epoch slicing, normalization, and sequence
packaging. The resulting sequences and labels are saved in a standardized
directory structure.

Example
-------
    sleepkit-preprocess \\
        --dataset SHHS1 \\
        --data-root /path/to/raw \\
        --out-root  /path/to/output

The CLI acts as a wrapper around the same preprocessing logic used by
the library API, enabling batch processing without writing Python code.
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
    """
    Entry point for the SleepKit command-line preprocessing tool.

    This function parses command-line arguments, loads dataset-specific
    rules, scans raw PSG files, matches annotation files, processes each
    subject, and writes standardized NumPy outputs.

    Command-Line Arguments
    ----------------------
    --dataset : str (required)
        Name of the dataset defined in ``config.DATASET_RULES``.
        Example: ``SHHS1``, ``ABC``, ``ISRUC``.
    --data-root : str (required)
        Root directory containing raw PSG data.
    --out-root : str (required)
        Output directory where ``seq/`` and ``label/`` folders will be saved.

    Output Structure
    ----------------
    out_root/
        dataset_name/
            seq/
                subject_id/
                    subject_id-0000.npy
                    subject_id-0001.npy
            label/
                subject_id/
                    subject_id-0000.npy
                    subject_id-0001.npy

    Notes
    -----
    - All preprocessing logic follows the standard SleepKit workflow.
    - This CLI is suitable for large-scale batch conversion.
    - Annotation matching uses both exact and fuzzy strategies.
    """
    parser = argparse.ArgumentParser(description="SleepKit PSG Processing")
    parser.add_argument('--dataset', required=True,
                        help="Dataset name in config (e.g., SHHS1)")
    parser.add_argument('--data-root', required=True,
                        help="Path to raw data directory")
    parser.add_argument('--out-root', required=True,
                        help="Directory to save processed output")
    args = parser.parse_args()

    dataset = args.dataset
    data_root = args.data_root
    out_dir = os.path.join(args.out_root, dataset)

    # ------------------------------------------------------------------
    # Prepare output folders
    # ------------------------------------------------------------------
    os.makedirs(os.path.join(out_dir, 'seq'), exist_ok=True)
    os.makedirs(os.path.join(out_dir, 'label'), exist_ok=True)

    # ------------------------------------------------------------------
    # Load dataset configuration
    # ------------------------------------------------------------------
    rules = DATASET_RULES.get(dataset, DATASET_RULES['SHHS1'])
    config = DEFAULT_PROCESS_CONFIG

    print(f"Dataset: {dataset}")
    print(f"Rules: {rules}")

    # ------------------------------------------------------------------
    # Scan for PSG and annotation files
    # ------------------------------------------------------------------
    print("Scanning files...")
    psg_ext = rules['fmt_psg']
    anno_ext = rules['fmt_anno']

    psg_files = sorted(glob.glob(os.path.join(data_root, '**', f'*.{psg_ext}'), recursive=True))
    anno_files = sorted(glob.glob(os.path.join(data_root, '**', f'*.{anno_ext}'), recursive=True))

    print(f"Found {len(psg_files)} PSGs, {len(anno_files)} Annos")

    # Map annotation files by base name
    anno_map = {os.path.splitext(os.path.basename(f))[0]: f for f in anno_files}

    # ------------------------------------------------------------------
    # Main processing loop
    # ------------------------------------------------------------------
    for psg_path in tqdm(psg_files):
        try:
            stem = os.path.splitext(os.path.basename(psg_path))[0]

            # Fuzzy annotation matching (base or substring)
            anno_path = anno_map.get(stem)
            if not anno_path:
                for k, v in anno_map.items():
                    if stem in k or k in stem:
                        anno_path = v
                        break

            if not anno_path:
                continue

            # --------------------------------------------------------------
            # Load raw signal and annotation
            # --------------------------------------------------------------
            raw, matched_chns = psg_load_raw(psg_path, dataset)
            if not raw:
                continue

            labels = load_annotation(anno_path, rules['reader'])
            if not labels:
                continue

            # --------------------------------------------------------------
            # Process channels according to config
            # --------------------------------------------------------------
            target_channels = config['channels']
            sigs = []

            for target in target_channels:
                real_name = matched_chns.get(target)
                if not real_name:
                    break

                # Reference electrode inference
                ref_target = None
                if target in ['F4', 'C4', 'O2']:
                    ref_target = 'M1'
                if target in ['F3', 'C3', 'O1']:
                    ref_target = 'M2'

                real_ref = matched_chns.get(ref_target)

                # Filter selection
                ftype = 'emg' if 'EMG' in target else 'eeg'

                s = process_single_channel(
                    raw, real_name, real_ref,
                    config['sample_rate'],
                    {
                        'bp': config['filter'][ftype],
                        'notch': config['filter']['notch']
                    }
                )

                if s is not None:
                    sigs.append(s)

            if len(sigs) != len(target_channels):
                continue

            # --------------------------------------------------------------
            # Epoch processing
            # --------------------------------------------------------------
            signal_data = np.stack(sigs)

            epochs, l_epochs = slice_epochs(signal_data, labels, config['sample_rate'])
            if epochs is None:
                continue

            # Standardization
            if config['standardize']:
                epochs = standardize_epochs(epochs)

            # Package into sequences
            seqs, l_seqs = package_sequences(epochs, l_epochs, config['seq_len'])
            if seqs is None:
                continue

            # --------------------------------------------------------------
            # Save outputs
            # --------------------------------------------------------------
            stem_safe = stem.replace('.', '_')

            subj_seq_dir = os.path.join(out_dir, 'seq', stem_safe)
            subj_lbl_dir = os.path.join(out_dir, 'label', stem_safe)
            os.makedirs(subj_seq_dir, exist_ok=True)
            os.makedirs(subj_lbl_dir, exist_ok=True)

            for i in range(len(seqs)):
                np.save(os.path.join(subj_seq_dir, f'{stem_safe}-{i}.npy'),
                        seqs[i].astype(np.float32))
                np.save(os.path.join(subj_lbl_dir, f'{stem_safe}-{i}.npy'),
                        l_seqs[i].astype(np.int64))

        except Exception:
            # Robust in CLI mode — skip problematic samples silently
            pass


if __name__ == '__main__':
    main()
