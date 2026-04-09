# PKGF Nature Analysis: Parallel Key Geometric Flow Framework

**A Unified Geometric Framework for Deterministic and Non-deterministic Information Memory**

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Fortran](https://img.shields.io/badge/Fortran-F90-orange.svg)](#)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](#)

## Overview

Natural observational data range from deterministic dynamical systems (e.g., Lorenz chaos, prime sequences) to non-deterministic phenomena (e.g., sunspots, heart rate variability, financial markets). Traditional AI models struggle to unify these disparate data types into a universal format.

**PKGF (Parallel Key Geometric Flow)** is a structural memory theory that remains agnostic to the generative origin of data. It maps raw signals into a 30-dimensional geometric feature vector ($\Phi$), embedding all information into a shared manifold. This repository contains the complete implementation, datasets, and theoretical documentation for the PKGF framework.

---

## Key Features

- **Structural Memory Mapping**: Extracts 30 indicators across 6 categories (Fractal, Information, Topology, Recurrence, Global, and Local geometry).
- **High-Performance Core**: Fortran-based mathematical core (`pkgf_math_core.f90`) for rapid extraction of Hurst exponents, fractal dimensions, and Fisher information.
- **Unified Pipeline**: Automated profiling, optimization (Nelder-Mead), and visualization of 21 natural datasets and 1 synthetic reference.
- **Geometric Flow Implementation**: Realizes information flow as an adjoint holonomy update on a Lie group.

---

## Repository Structure

```text
.
├── Data/            # 21 Raw datasets (*_raw), Synthetic models, and Morphic Profiles (.json)
├── Docs/            # Academic papers (EN/JP), Similarity maps, and Dataset lists
├── Scripts/         # Core implementation
│   ├── pkgf_master_pipeline.py  # Main orchestration pipeline
│   ├── pkgf_math_core.f90       # High-performance Fortran math core
│   └── cross_validate_fortran.py # Validation of Py/Fortran consistency
├── References/      # Foundational PDFs and text references
└── LICENSE          # Apache License 2.0
```

---

## Prerequisites

- **Fortran Compiler**: `gfortran` (for compiling the shared library)
- **Python 3.8+**:
  - `numpy`, `pandas`, `scipy`, `scikit-learn`, `matplotlib`
  - `ripser` (for TDA/Topological Data Analysis)
  - `ctypes` (for Fortran-Python bridging)

---

## Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/aikenkyu001/PKGF_nature_analysis.git
   cd PKGF_nature_analysis
   ```

2. **Compile the Fortran Mathematical Core (Optional but recommended)**:
   High-performance calculations for Hurst, Fractal, and Fisher metrics.
   ```bash
   gfortran -O3 -shared -fPIC -o Scripts/pkgf_math_core.so Scripts/pkgf_math_core.f90
   ```

3. **Install Python dependencies**:
   ```bash
   pip install numpy pandas scipy scikit-learn matplotlib ripser
   ```

---

## Usage

### 1. Mathematical Backend Switching
PKGF supports dual backends. You can switch between pure Python (for ease of setup) and Fortran (for performance) using the `--backend` flag.

**Run with Python Backend (Default):**
```bash
python Scripts/pkgf_master_pipeline.py --backend python
```

**Run with Fortran Backend (High Performance):**
```bash
python Scripts/pkgf_master_pipeline.py --backend fortran
```
*Note: If the Fortran library is not compiled, the system will automatically fall back to the Python backend.*

### 2. Validation
To ensure that both backends produce identical mathematical results, run the cross-validation script:
```bash
python Scripts/cross_validate_fortran.py
```
This script compares Hurst Exponents, Fractal Dimensions, and Fisher Information across both implementations using real-world datasets.

### 3. Full Pipeline Execution
The master pipeline performs:
- **Profiling**: Extracts 30 geometric features from 21 datasets.
- **Optimization**: Tunes logic primitives to match natural structural profiles.
- **Visualization**: Generates `similarity_map.png` and `model_character_comparison.png` in `Docs/`.

---

## Datasets

The framework analyzes **21 natural observational datasets** across four categories:
1. **Space & Physics**: Sunspots, Solar Flares, Geomagnetic, Cosmic Rays, Star Brightness.
2. **Earth Science**: Nile Levels, CO2, Sea Level, Ice Core, Treerings, Atmospheric Noise, Geyser, Seismic.
3. **Biology & Social**: Heart Rate Variability (HRV), Bitcoin, Network Traffic, Hydrothermal.
4. **Mathematics**: Prime distribution, Prime Gaps, Lorenz system.

---

## Theoretical Foundation

PKGF is built upon 7 Axioms and 5 Theorems, as detailed in `Docs/Unified_PKGF_Theory.md`.

- **Axiom P1**: Decomposition of the Tangent Bundle into Input, Memory, Flow, and Output sectors.
- **Theorem 1 (Invariance of Logic)**: Conservation of $\det(K)$ during geometric flow.
- **Theorem 5 (Universality)**: Behavior of the flow is identical if the structural mapping $\Phi$ is identical, regardless of the data origin.

---

## Citation

If you use this framework or datasets in your research, please refer to the following:
- **DOI**: [10.5281/zenodo.19477743](https://doi.org/10.5281/zenodo.19477743)
- **Paper**: *PKGF: A Unified Geometric Framework for Deterministic and Non-deterministic Information Memory* (Fumio Miyata, 2026)

## License

This project is licensed under the **Apache License 2.0**. See the [LICENSE](LICENSE) file for details.
