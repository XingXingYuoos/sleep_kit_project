import os
import glob
import numpy as np
from tqdm import tqdm

from .config import DATASET_RULES, DEFAULT_PROCESS_CONFIG
from .io import psg_load_raw
from .annotation import load_annotation
from .signal_proc import process_single_channel
from .epoch import slice_epochs, standardize_epochs, package_sequences


def fast_preprocess(dataset_name, data_root, out_root,
                    channels=['F4', 'E1'],
                    fs=100,
                    seq_len=20,
                    overwrite=False):
    """
    Fast preprocessing pipeline for multi-center PSG datasets.

    This utility performs a complete PSG-to-Numpy conversion with minimal
    configuration. It loads raw recordings, extracts specified channels,
    applies standard filtering, converts to fixed-length epochs, packages
    them into sequences, and saves them in NumPy format.

    Parameters
    ----------
    dataset_name : str
        Name of the dataset. Must be defined in ``config.DATASET_RULES``.
        Example: ``'SHHS1'``, ``'ABC'``, ``'ISRUC'``.
    data_root : str
        Root directory containing the raw PSG files.
    out_root : str
        Output directory where processed data will be stored.
    channels : list of str, optional
        EEG/EMG channel names to extract. Default is ``['F4', 'E1']``.
    fs : int, optional
        Target sampling frequency. Default is ``100``.
    seq_len : int, optional
        Number of epochs per sequence. Default is ``20``.
    overwrite : bool, optional
        Whether to overwrite existing output folders. Default is ``False``.

    Notes
    -----
    - This function aims to provide a lightweight, unified preprocessing
      interface for heterogeneous PSG datasets.
    - Channel names are internally mapped based on dataset-specific rules.
    - Epoch slicing, normalization, and sequence packaging follow a
      standardized pipeline to ensure cross-dataset consistency.

    Returns
    -------
    None
        All results are written to ``out_root/dataset_name``.

    Output Directory Structure
    --------------------------
    out_root/
        dataset_name/
            seq/
                subject_id/
                    subject_id-0000.npy
                    subject_id-0001.npy
                    ...
            label/
                subject_id/
                    subject_id-0000.npy
                    subject_id-0001.npy
                    ...
    """
    # ----------------------------------------------------------------------
    # Prepare output paths
    # ----------------------------------------------------------------------
    out_dir = os.path.join(out_root, dataset_name)
    seq_dir = os.path.join(out_dir, 'seq')
    label_dir = os.path.join(out_dir, 'label')

    if os.path.exists(out_dir) and not overwrite:
        print(f"Warning: Output directory {out_dir} already exists. Use overwrite=True to force.")
        # return

    os.makedirs(seq_dir, exist_ok=True)
    os.makedirs(label_dir, exist_ok=True)

    # Load dataset rules (format, annotation, reader, etc.)
    rules = DATASET_RULES.get(dataset_name)
    if not rules:
        print(f"Error: Dataset '{dataset_name}' not found in configuration rules.")
        return

    # Default filtering configuration
    filter_cfg = DEFAULT_PROCESS_CONFIG['filter']

    print(f"Start Processing: {dataset_name}")
    print(f"Data Root: {data_root}")
    print(f"Target Channels: {channels} @ {fs}Hz")

    # ----------------------------------------------------------------------
    # Scan input files
    # ----------------------------------------------------------------------
    psg_pattern = os.path.join(data_root, '**', f'*.{rules["fmt_psg"]}')
    anno_pattern = os.path.join(data_root, '**', f'*.{rules["fmt_anno"]}')

    psg_files = sorted(glob.glob(psg_pattern, recursive=True))
    anno_files = sorted(glob.glob(anno_pattern, recursive=True))

    # Build a name-to-path mapping for fast annotation matching
    anno_map = {os.path.splitext(os.path.basename(f))[0]: f for f in anno_files}

    print(f"Found {len(psg_files)} PSG files.")

    # ----------------------------------------------------------------------
    # Process each subject
    # ----------------------------------------------------------------------
    success_count = 0
    for psg_path in tqdm(psg_files, desc=f"Processing {dataset_name}"):
        try:
            stem = os.path.splitext(os.path.basename(psg_path))[0]

            # Match annotation file with a flexible strategy
            anno_path = anno_map.get(stem)
            if not anno_path:
                for k, v in anno_map.items():
                    if stem in k or k in stem:
                        anno_path = v
                        break
            if not anno_path:
                continue

            # ------------------------------------------------------------------
            # Load raw PSG and annotation
            # ------------------------------------------------------------------
            raw, matched_chns = psg_load_raw(psg_path, dataset_name)
            if not raw:
                continue

            labels = load_annotation(anno_path, rules['reader'])
            if not labels:
                continue

            # ------------------------------------------------------------------
            # Extract and filter selected channels
            # ------------------------------------------------------------------
            sigs = []
            for target in channels:
                real_name = matched_chns.get(target)
                if not real_name:
                    break  # Missing required channel

                # Auto-reference selection
                ref_target = 'M1' if target in ['F4', 'C4', 'O2'] else 'M2'
                if target in ['F3', 'C3', 'O1']:
                    ref_target = 'M2'
                if 'EMG' in target:
                    ref_target = None

                real_ref = matched_chns.get(ref_target)

                ftype = 'emg' if 'EMG' in target else 'eeg'

                sig = process_single_channel(
                    raw, real_name, real_ref, fs,
                    {'bp': filter_cfg[ftype], 'notch': filter_cfg['notch']}
                )
                if sig is not None:
                    sigs.append(sig)

            if len(sigs) != len(channels):
                continue

            # ------------------------------------------------------------------
            # Epoching, normalization, and sequence packaging
            # ------------------------------------------------------------------
            signal_data = np.stack(sigs)  # shape: (C, T)

            epochs, l_epochs = slice_epochs(signal_data, labels, fs)
            if epochs is None:
                continue

            epochs = standardize_epochs(epochs)

            seqs, l_seqs = package_sequences(epochs, l_epochs, seq_len)
            if seqs is None:
                continue

            # ------------------------------------------------------------------
            # Save results in NumPy format
            # ------------------------------------------------------------------
            stem_safe = stem.replace('.', '_')
            subj_seq_dir = os.path.join(seq_dir, stem_safe)
            subj_lbl_dir = os.path.join(label_dir, stem_safe)
            os.makedirs(subj_seq_dir, exist_ok=True)
            os.makedirs(subj_lbl_dir, exist_ok=True)

            for i in range(len(seqs)):
                np.save(os.path.join(subj_seq_dir, f'{stem_safe}-{i}.npy'),
                        seqs[i].astype(np.float32))
                np.save(os.path.join(subj_lbl_dir, f'{stem_safe}-{i}.npy'),
                        l_seqs[i].astype(np.int64))

            success_count += 1

        except Exception:
            # In production, consider logging instead of printing
            pass

    print(f"Finished. Successfully processed {success_count} subjects.")
