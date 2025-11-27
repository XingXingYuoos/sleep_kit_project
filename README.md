
# 🇨🇳 **中文版 README（SleepKit 中文文档）**

<div align="center">
  <img src="SleepKit.png" alt="SleepKit Logo" width="400">
</div>

# SleepKit PSG：多数据集睡眠 PSG 预处理框架

SleepKit PSG 是一个模块化、高度工程化的 Python 框架，专为多源多导睡眠图（Polysomnography, PSG）数据的标准化预处理而设计。
它能够将来自不同数据集（如 SHHS, MESA, CFS, Sleep-EDF 等）、不同格式（EDF, H5, MAT）的原始数据，统一转换为适合深度学习模型输入的标准格式（`.npy` 序列）。

---

## 🌟 核心功能

### ◎ 多数据集支持

内置 20+ 主流公开睡眠数据集的规则（SHHS, MESA, CFS, MASS, DOD, Sleep-EDF …）。

### ◎ 智能通道映射

自动识别并统一不同数据集中的通道名称（如将 `EEG(sec)` 自动识别为 `C3`）。

### ◎ 完整标准化预处理流程

包含：

* 多格式文件读取（EDF / H5 / MAT）
* 多标签格式解析（XML / TXT / CSV / EANNOT）
* 预处理（重参考、带通滤波、陷波、重采样、Z-Score）
* Epoch 切片 + 序列打包

### ◎ 提供 CLI + Python API

既能批处理，也能直接插入现有项目。

---

## 🛠️ 安装

### 环境要求

* Python ≥ 3.8
* numpy, mne, h5py, scipy, sklearn, matplotlib, tqdm, pyyaml

### 方式一：直接安装

```bash
cd sleep_kit_project
pip install .
```

### 方式二：构建 Wheel 包

```bash
pip install build
python -m build
pip install dist/sleep_kit_psg-0.1.0-py3-none-any.whl --force-reinstall
```

---

## 🚀 快速开始（Usage）

SleepKit 支持两种使用方式：CLI 与 Python API。

---

### 方式一：命令行工具（CLI）

```bash
sleepkit-process --dataset SHHS1 --data-root <原始数据路径> --out-root <输出目录>
```

参数说明：

| 参数            | 含义             |
| ------------- | -------------- |
| `--dataset`   | 数据集名称（如 SHHS1） |
| `--data-root` | EDF/XML 的根目录   |
| `--out-root`  | 输出目录           |

示例：

```bash
sleepkit-process \
    --dataset SHHS1 \
    --data-root /public_data/nsrr/shhs/polysomnography \
    --out-root /data/processed/sleep_data
```

---

### 方式二：Python API

创建 `run.py`：

```python
import sleep_kit

raw_dir = r'/public_data/nsrr/shhs/polysomnography'
out_dir = r'/data/output_test'

sleep_kit.fast_preprocess(
    dataset_name='SHHS1',
    data_root=raw_dir,
    out_root=out_dir,
    channels=['C4', 'E1'],
    fs=100,
    seq_len=20,
    max_subjects=5
)
```

运行：

```bash
python run.py
```

---

## 📂 输出结构

```text
/output/
└── SHHS1/
    ├── seq/
    │   ├── shhs1-200001-0.npy   # (Seq, C, T)
    │   ├── shhs1-200001-1.npy
    └── label/
        ├── shhs1-200001-0.npy   # (Seq,)
```

---

## ⚙️ 默认配置（config.py）

* 采样率：100 Hz
* Epoch：30 s
* EEG 带通：0.3–35 Hz
* EMG 带通：10–49 Hz
* 工频陷波：50/60 Hz

支持数据集：

`SHHS1`, `SHHS2`, `MESA`, `CFS`, `CCSHS`, `MROS1`, `MROS2`, `ABC`, `HMC`, `MASS13`, `DOD`, etc.

---

## 📝 常见问题（FAQ）

### ❓ 为什么输出 0 个被试？

因为 `data_root` 设置过深，应指向 **EDF + 标签文件所在的上级目录**。

### ❓ 如何添加新数据集？

在 `config.py`：

1. 添加通道映射
2. 添加 DATASET_RULE

### ❓ ImportError: No module named sleep_kit

请确保在项目根目录运行：

```bash
pip install .
```
---

_**如有问题，请联系作者：**jinyang03702@163.com****_

---

# **English Version README（SleepKit Documentation）**

<div align="center">
  <img src="SleepKit.png" alt="SleepKit Logo" width="400">
</div>

# SleepKit PSG: A Multi-Dataset PSG Preprocessing Framework

SleepKit PSG is a modular and engineering-oriented Python framework designed for standardized preprocessing of multi-source, multi-channel polysomnography (PSG) data.
It converts heterogeneous datasets (SHHS, MESA, CFS, Sleep-EDF, etc.) and formats (EDF, H5, MAT) into standardized `.npy` sequences for deep learning models.

---

## 🌟 Key Features

### ◎ Multi-Dataset Support

Built-in rules for 20+ major public PSG datasets.

### ◎ Intelligent Channel Mapping

Automatically unifies inconsistent channel names across datasets (e.g., `EEG(sec)` → `C3`).

### ◎ Full Preprocessing Pipeline

Includes:

* Multi-format reading (EDF / H5 / MAT)
* Sleep-stage label parsing (XML / TXT / CSV / EANNOT)
* Signal processing (re-reference, bandpass, notch, resample, Z-score)
* Epoch slicing and sequence packaging

### ◎ CLI + Python API

Supports both batch processing and programmatic use.

---

## 🛠️ Installation

### Requirements

* Python ≥ 3.8
* numpy, mne, h5py, scipy, sklearn, matplotlib, tqdm, pyyaml

### Method 1: Install directly

```bash
cd sleep_kit_project
pip install .
```

### Method 2: Build a wheel

```bash
pip install build
python -m build
pip install dist/sleep_kit_psg-0.1.0-py3-none-any.whl --force-reinstall
```

---

## 🚀 Quick Start

SleepKit supports **CLI** and **Python API**.

---

### Method 1: CLI

```bash
sleepkit-process --dataset SHHS1 --data-root <raw_data> --out-root <output_dir>
```

Arguments:

| Parameter     | Description               |
| ------------- | ------------------------- |
| `--dataset`   | Dataset name              |
| `--data-root` | Root directory of EDF/XML |
| `--out-root`  | Output directory          |

Example:

```bash
sleepkit-process \
    --dataset SHHS1 \
    --data-root /public_data/nsrr/shhs/polysomnography \
    --out-root /data/processed/sleep_data
```

---

### Method 2: Python API

Create `run.py`:

```python
import sleep_kit

raw_dir = r'/public_data/nsrr/shhs/polysomnography'
out_dir = r'/data/output_test'

sleep_kit.fast_preprocess(
    dataset_name='SHHS1',
    data_root=raw_dir,
    out_root=out_dir,
    channels=['C4', 'E1'],
    fs=100,
    seq_len=20,
    max_subjects=5
)
```

Run:

```bash
python run.py
```

---

## 📂 Output Structure

```text
/output/
└── SHHS1/
    ├── seq/
    │   ├── shhs1-200001-0.npy   # (Seq, C, T)
    │   ├── shhs1-200001-1.npy
    └── label/
        ├── shhs1-200001-0.npy   # (Seq,)
```

---

## ⚙️ Default Settings (config.py)

* Sampling rate: 100 Hz
* Epoch length: 30 s
* EEG bandpass: 0.3–35 Hz
* EMG bandpass: 10–49 Hz
* Notch: 50/60 Hz

Supported datasets:

`SHHS1`, `SHHS2`, `MESA`, `CFS`, `CCSHS`, `MROS1`, `MROS2`, `ABC`, `HMC`, `MASS13`, `DOD`, etc.

---

## 📝 FAQ

### ❓ Why does it process 0 subjects?

Because `data_root` is set too deep; it must point to the parent directory of EDF + annotation.

### ❓ How to add a new dataset?

Modify:

1. `CHANNEL_MAPPING`
2. `DATASET_RULES`

### ❓ ImportError: No module named sleep_kit

Run:

```bash
pip install .
```

---
**For any issues or inquiries, please contact the author at: **jinyang03702@163.com****

