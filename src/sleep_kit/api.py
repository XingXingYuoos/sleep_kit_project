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
    极简的一键预处理函数。

    Args:
        dataset_name (str): 数据集名称 (如 'SHHS1', 'ABC')，必须在 config.py 中有定义。
        data_root (str): 原始数据根目录。
        out_root (str): 输出目录。
        channels (list): 需要提取的通道列表，默认为 ['F4', 'E1']。
        fs (int): 目标采样率，默认为 100。
        seq_len (int): 序列长度 (Epoch数)，默认为 20。
        overwrite (bool): 是否覆盖已存在的输出文件夹。

    Returns:
        None
    """
    # 1. 准备路径
    out_dir = os.path.join(out_root, dataset_name)
    seq_dir = os.path.join(out_dir, 'seq')
    label_dir = os.path.join(out_dir, 'label')

    if os.path.exists(out_dir) and not overwrite:
        print(f"Warning: Output directory {out_dir} already exists. Use overwrite=True to force.")
        # 这里可以选择直接返回，或者继续（可能会混合旧文件）
        # return

    os.makedirs(seq_dir, exist_ok=True)
    os.makedirs(label_dir, exist_ok=True)

    # 获取规则 (如果数据集未定义，默认回退到 SHHS1 规则，实际使用建议抛出异常)
    rules = DATASET_RULES.get(dataset_name)
    if not rules:
        print(f"Error: Dataset '{dataset_name}' not found in configuration rules.")
        return

    # 默认滤波配置
    filter_cfg = DEFAULT_PROCESS_CONFIG['filter']

    print(f"Start Processing: {dataset_name}")
    print(f"Data Root: {data_root}")
    print(f"Target Channels: {channels} @ {fs}Hz")

    # 2. 扫描文件
    # 递归查找所有匹配扩展名的文件
    psg_pattern = os.path.join(data_root, '**', f'*.{rules["fmt_psg"]}')
    anno_pattern = os.path.join(data_root, '**', f'*.{rules["fmt_anno"]}')

    psg_files = sorted(glob.glob(psg_pattern, recursive=True))
    anno_files = sorted(glob.glob(anno_pattern, recursive=True))

    # 建立文件名(无后缀)到完整路径的映射，用于快速匹配
    anno_map = {os.path.splitext(os.path.basename(f))[0]: f for f in anno_files}

    print(f"Found {len(psg_files)} PSG files.")

    # 3. 循环处理
    success_count = 0
    for psg_path in tqdm(psg_files, desc=f"Processing {dataset_name}"):
        try:
            stem = os.path.splitext(os.path.basename(psg_path))[0]

            # 3.1 匹配标签 (模糊匹配策略)
            anno_path = anno_map.get(stem)
            if not anno_path:
                # 尝试包含匹配 (例如 shhs1-200001 匹配 shhs1-200001-profusion.xml)
                for k, v in anno_map.items():
                    if stem in k or k in stem:
                        anno_path = v;
                        break

            if not anno_path:
                # print(f"Skipping {stem}: Annotation not found.")
                continue

            # 3.2 读取数据
            raw, matched_chns = psg_load_raw(psg_path, dataset_name)
            if not raw: continue

            labels = load_annotation(anno_path, rules['reader'])
            if not labels: continue

            # 3.3 处理通道 (核心循环)
            sigs = []
            for target in channels:
                real_name = matched_chns.get(target)
                if not real_name: break  # 缺少关键通道，跳过此人

                # 智能推断参考电极 (M1/M2)
                ref_target = 'M1' if target in ['F4', 'C4', 'O2'] else 'M2'
                if target in ['F3', 'C3', 'O1']: ref_target = 'M2'
                if 'EMG' in target: ref_target = None  # EMG通常不需要额外参考

                real_ref = matched_chns.get(ref_target)

                # 选择滤波器 (EEG 或 EMG)
                ftype = 'emg' if 'EMG' in target else 'eeg'

                s = process_single_channel(
                    raw, real_name, real_ref, fs,
                    {'bp': filter_cfg[ftype], 'notch': filter_cfg['notch']}
                )
                if s is not None: sigs.append(s)

            if len(sigs) != len(channels): continue  # 通道不全，跳过

            # 3.4 切片与保存
            signal_data = np.stack(sigs)  # (C, T)
            epochs, l_epochs = slice_epochs(signal_data, labels, fs)
            if epochs is None: continue

            # 标准化
            epochs = standardize_epochs(epochs)
            # 序列化
            seqs, l_seqs = package_sequences(epochs, l_epochs, seq_len)
            if seqs is None: continue

            # 保存为 numpy
            stem_safe = stem.replace('.', '_')
            subj_seq_dir = os.path.join(seq_dir, stem_safe)
            subj_lbl_dir = os.path.join(label_dir, stem_safe)
            os.makedirs(subj_seq_dir, exist_ok=True)
            os.makedirs(subj_lbl_dir, exist_ok=True)

            for i in range(len(seqs)):
                np.save(os.path.join(subj_seq_dir, f'{stem_safe}-{i}.npy'), seqs[i].astype(np.float32))
                np.save(os.path.join(subj_lbl_dir, f'{stem_safe}-{i}.npy'), l_seqs[i].astype(np.int64))

            success_count += 1

        except Exception as e:
            # 生产环境建议记录日志而不是打印
            # print(f"Error processing {stem}: {e}")
            pass

    print(f"Finished. Successfully processed {success_count} subjects.")