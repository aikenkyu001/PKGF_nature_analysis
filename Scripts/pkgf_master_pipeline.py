import csv
import json
import os
import glob
import argparse
import ctypes
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Literal
from scipy.optimize import minimize
from sklearn.neighbors import NearestNeighbors
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import pairwise_distances

# ============================================================
# 1. Configuration & Constants
# ============================================================
DATA_DIR = "Data"
DOCS_DIR = "Docs"
os.makedirs(DOCS_DIR, exist_ok=True)

OUTPUT_REPORT = os.path.join(DOCS_DIR, "primitive_matching_report.csv")
SIMILARITY_MAP = os.path.join(DOCS_DIR, "similarity_map.png")
CHARACTER_MAP = os.path.join(DOCS_DIR, "model_character_comparison.png")

PRIMITIVE_ID_DATA_RECOVERY = 200

# ============================================================
# 2. Utility & Base Math Primitives
# ============================================================

def _safe(x):
    x = np.asarray(x); x = x[np.isfinite(x)]
    return float(np.mean(x)) if len(x) > 0 else 0.0

def _safe_std(x):
    x = np.asarray(x); x = x[np.isfinite(x)]
    return float(np.std(x)) if len(x) > 0 else 0.0

def _safe_mean(x):
    x = np.asarray(x); x = x[np.isfinite(x)]
    return float(np.mean(x)) if len(x) > 0 else 0.0

def _safe_max(x):
    x = np.asarray(x); x = x[np.isfinite(x)]
    return float(np.max(x)) if len(x) > 0 else 0.0

def _subsample(X, max_n=300, seed=0):
    X = np.asarray(X)
    if len(X) > max_n:
        rng = np.random.default_rng(seed)
        idx = rng.choice(len(X), max_n, replace=False)
        return X[idx]
    return X

def rank_normalize(df):
    """Normalize features by rank to eliminate outlier dominance and unify distributions."""
    return df.rank(method="average") / len(df)

def _entropy_hist(x, bins=32):
    hist, _ = np.histogram(x, bins=bins, density=True)
    hist = hist[hist > 0]
    return float(-np.sum(hist * np.log(hist + 1e-12)))

def takens_embedding(ts, dim=3, tau=1):
    ts = np.asarray(ts).ravel(); N = len(ts) - (dim - 1) * tau
    if N <= 0: return np.zeros((1, dim))
    return np.array([ts[i:i + dim * tau:tau] for i in range(N)])

def fbm_generate(n, H):
    """Generates Fractional Gaussian Noise (approximation)"""
    if n < 2: return np.zeros(n)
    freq = np.fft.fftfreq(n); psd = np.zeros_like(freq)
    safe_H = np.clip(H, 0.01, 0.99)
    psd[1:] = np.abs(freq[1:])**(-(2*safe_H - 1))
    noise = np.real(np.fft.ifft(np.fft.fft(np.random.normal(0, 1, n)) * np.sqrt(psd)))
    std = np.std(noise)
    return noise / std if std > 0 else noise

def generate_primitive_signal(n, params):
    mu, sigma, H, trend_slope = params
    t = np.arange(n); trend = trend_slope * (t / n)
    noise = fbm_generate(n, H)
    return mu + trend + sigma * noise

# ============================================================
# 3. Math Backend Manager (Python / Fortran Switch)
# ============================================================

class MathBackend:
    def __init__(self, mode: Literal["python", "fortran"] = "python"):
        self.mode = mode
        self.fortran_lib = None
        if mode == "fortran":
            try:
                # Resolve path relative to project root
                lib_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "pkgf_math_core.so"))
                if not os.path.exists(lib_path):
                    print(f"[!] Warning: {lib_path} not found. Please compile it using gfortran.")
                    print("    Command: gfortran -O3 -shared -fPIC -o Scripts/pkgf_math_core.so Scripts/pkgf_math_core.f90")
                    print("    Falling back to Python backend.")
                    self.mode = "python"
                else:
                    self.fortran_lib = ctypes.CDLL(lib_path)
                    # Define signatures
                    self.fortran_lib.compute_hurst.argtypes = [ctypes.c_int, np.ctypeslib.ndpointer(dtype=np.float64), ctypes.POINTER(ctypes.c_double)]
                    self.fortran_lib.compute_fractal_dim.argtypes = [ctypes.c_int, np.ctypeslib.ndpointer(dtype=np.float64), ctypes.POINTER(ctypes.c_double)]
                    # Correct order: (n, x, bins, f_val) -> (int, double*, int, double*)
                    self.fortran_lib.compute_fisher.argtypes = [ctypes.c_int, np.ctypeslib.ndpointer(dtype=np.float64), ctypes.c_int, ctypes.POINTER(ctypes.c_double)]
                    print(f"[*] MathBackend initialized in FORTRAN mode.")
            except Exception as e:
                print(f"[!] Fortran Load Error: {e}. Falling back to Python.")
                self.mode = "python"
        
        if self.mode == "python":
            print(f"[*] MathBackend initialized in PYTHON mode.")

    def hurst(self, ts):
        if self.mode == "fortran":
            ts_c = np.ascontiguousarray(ts, dtype=np.float64)
            val = ctypes.c_double()
            self.fortran_lib.compute_hurst(len(ts_c), ts_c, ctypes.byref(val))
            return float(val.value)
        return hurst_exponent(ts)

    def fractal_dim(self, ts):
        if self.mode == "fortran":
            ts_c = np.ascontiguousarray(ts, dtype=np.float64)
            val = ctypes.c_double()
            self.fortran_lib.compute_fractal_dim(len(ts_c), ts_c, ctypes.byref(val))
            return float(val.value)
        return fractal_dimension(ts)

    def fisher(self, ts, bins=32):
        if self.mode == "fortran":
            ts_c = np.ascontiguousarray(ts, dtype=np.float64)
            val = ctypes.c_double()
            # Correct call: (n, x, bins, f_val)
            self.fortran_lib.compute_fisher(len(ts_c), ts_c, bins, ctypes.byref(val))
            return float(val.value)
        return fisher_information(ts, bins)

# Global backend instance (default to python, will be updated by pipeline)
_backend = MathBackend(mode="python")

# ============================================================
# 4. Structural Feature Engines (100% Original Restoration)
# ============================================================

def local_structure_features(X, k_list=(5, 10, 20)):
    feats = {}
    n = len(X)
    if n < 2: return feats
    for k in k_list:
        k_eff = min(k, n - 1)
        if k_eff < 2: continue
        nn = NearestNeighbors(n_neighbors=k_eff + 1).fit(X)
        dists, idx = nn.kneighbors(X)
        d_log = np.log(dists[:, 1:] + 1e-8)
        feats[f"knn{k}_mean"] = _safe(d_log)
        feats[f"knn{k}_std"] = _safe_std(d_log)
        dims = []
        for i in range(n):
            neigh = X[idx[i, 1:]]
            if len(neigh) < 2: continue
            pca = PCA().fit(neigh)
            dim = 1 + int(np.argmax(np.cumsum(pca.explained_variance_ratio_) >= 0.9))
            dims.append(dim)
        feats[f"local_dim{k}_mean"] = _safe(dims)
        feats[f"local_dim{k}_std"] = _safe_std(dims)
    return feats

def global_structure_features(X):
    n, p = X.shape
    if n < 2 or p < 1: return {}
    pca = PCA().fit(X); ev = pca.explained_variance_ratio_
    dim_90 = 1 + int(np.argmax(np.cumsum(ev) >= 0.9))
    return {"global_dim90": int(dim_90), "ev1": float(ev[0]) if len(ev) > 0 else 0.0,
            "ev2": float(ev[1]) if len(ev) > 1 else 0.0, "ev3": float(ev[2]) if len(ev) > 2 else 0.0}

def tda_features(X):
    X_sub = _subsample(X, 300)
    try:
        from ripser import ripser
    except ImportError:
        return {"tda_betti0": 0.0, "tda_betti1": 0.0, "tda_life_mean": 0.0, "tda_life_max": 0.0}
    res = ripser(X_sub, maxdim=1); dgms = res["dgms"]
    lengths, betti = [], [0, 0]
    for dim, dgm in enumerate(dgms):
        if len(dgm) == 0: continue
        life = dgm[:, 1] - dgm[:, 0]
        life = life[np.isfinite(life)]; lengths.extend(life.tolist())
        if dim < 2: betti[dim] = len(life)
    return {"tda_betti0": float(betti[0]), "tda_betti1": float(betti[1]),
            "tda_life_mean": _safe_mean(lengths), "tda_life_max": _safe_max(lengths)}

def multifractal_features(ts, q_list=(-5, -2, 0, 2, 5)):
    ts = np.asarray(ts).ravel(); ts = ts - np.mean(ts); Y = np.cumsum(ts); N = len(Y)
    max_s = N // 4
    if max_s < 16: return {"mf_width": 0.0, "mf_singularity": 0.0, "mf_asymmetry": 0.0}
    scales = np.unique(np.logspace(np.log10(8), np.log10(max_s), 10).astype(int))
    h_q = []
    for q in q_list:
        F_s = []
        for s in scales:
            segments = N // s
            var_s = [max(np.mean((Y[i*s:(i+1)*s] - np.polyval(np.polyfit(np.arange(s), Y[i*s:(i+1)*s], 1), np.arange(s)))**2), 1e-12) for i in range(segments)]
            var_s = np.array(var_s)
            if q == 0: F_s.append(np.exp(0.5 * np.mean(np.log(var_s))))
            else: F_s.append((np.mean(var_s**(q/2.0)))**(1.0/q))
        F_s = np.array(F_s); F_s[F_s < 1e-12] = 1e-12
        h_q.append(np.polyfit(np.log(scales), np.log(F_s), 1)[0])
    q_arr, h_arr = np.array(q_list), np.array(h_q); tau_q = q_arr * h_arr - 1.0
    alpha = np.gradient(tau_q, q_arr); mf_width = float(np.max(alpha) - np.min(alpha))
    mf_singularity = float(alpha[len(alpha)//2])
    left, right = mf_singularity - np.min(alpha), np.max(alpha) - mf_singularity
    return {"mf_width": mf_width, "mf_singularity": mf_singularity, "mf_asymmetry": float(right/left if left > 1e-6 else 1.0)}

def hurst_exponent(ts):
    ts = np.asarray(ts).ravel(); N = len(ts)
    if N < 50: return 0.5
    max_scale = int(np.floor(np.log2(N))); sizes = [2**i for i in range(3, max_scale)]
    if not sizes: sizes = [8, 16, 32]
    RS, ns = [], []
    for s in sizes:
        n_seg = N // s; rs_seg = []
        for i in range(n_seg):
            seg = ts[i*s:(i+1)*s]
            if len(seg) < 2: continue
            Z = np.cumsum(seg - np.mean(seg)); R, S = np.max(Z) - np.min(Z), np.std(seg)
            if S > 1e-12: rs_seg.append(R / S)
        if rs_seg: RS.append(np.mean(rs_seg)); ns.append(s)
    if len(RS) < 2: return 0.5
    H, _ = np.polyfit(np.log(ns), np.log(RS), 1)
    return float(np.clip(H, 0.0, 1.0))

def fractal_dimension(ts):
    ts = np.asarray(ts).ravel(); N = len(ts)
    if N < 20: return 1.0
    scales = [2, 4, 8, 16, 32]; scales = [s for s in scales if s < N]
    counts, sizes = [], []
    for s in scales:
        bins = np.floor((ts - np.min(ts)) / (np.ptp(ts) + 1e-8) * s)
        counts.append(len(np.unique(bins))); sizes.append(1.0 / s)
    if len(counts) < 2: return 1.0
    D, _ = np.polyfit(np.log(sizes), np.log(counts), 1)
    return float(-D)

def fisher_information(ts, bins=32):
    ts = np.asarray(ts).ravel(); hist, edges = np.histogram(ts, bins=bins, density=True)
    p = hist + 1e-12; dx = edges[1] - edges[0]; dp = np.diff(p) / dx
    p_mid = (p[:-1] + p[1:]) / 2.0
    return float(np.log1p(np.sum((dp**2) / p_mid) * dx))

def rqa_features(ts, dim=3, tau=1):
    ts = _subsample(ts, 1500).ravel(); N = len(ts) - (dim - 1) * tau
    if N < 20: return {"rqa_rr": 0.0, "rqa_det": 0.0}
    X = np.array([ts[i:i+dim*tau:tau] for i in range(N)]); D = pairwise_distances(X)
    eps = np.quantile(D, 0.1); R = (D < eps).astype(int); RR = np.mean(R)
    diag = np.diag(R, k=1); DET = float(np.sum(diag) / np.sum(R)) if np.sum(R) > 0 else 0.0
    return {"rqa_rr": float(RR), "rqa_det": float(DET)}

def extract_all_features(X=None, ts=None):
    feats = {}
    if X is not None and len(X) >= 2:
        X_scaled = StandardScaler().fit_transform(X)
        feats.update(local_structure_features(X_scaled))
        feats.update(global_structure_features(X_scaled))
        feats.update(tda_features(X_scaled))
    if ts is not None and len(ts) >= 2:
        ts_scaled = StandardScaler().fit_transform(np.asarray(ts).reshape(-1, 1)).ravel()
        # Use backend-aware methods for Hurst, Fractal, and Fisher
        feats.update({"hurst": _backend.hurst(ts_scaled), "fractal_dim": _backend.fractal_dim(ts_scaled)})
        feats.update(multifractal_features(ts_scaled))
        feats.update({"fisher": _backend.fisher(ts_scaled)})
        feats.update(rqa_features(ts_scaled))
        feats.update({"var": float(np.var(ts_scaled)), "entropy": _entropy_hist(ts_scaled)})
    return feats

# ============================================================
# 5. Pipeline Orchestrator (Complete Fusion)
# ============================================================

class PKGFMasterPipeline:
    def __init__(self, backend_mode: Literal["python", "fortran"] = "python"):
        global _backend
        _backend = MathBackend(mode=backend_mode)
        self.profiles = {}

    def run_profiling(self):
        raw_files = glob.glob(os.path.join(DATA_DIR, "*_raw.csv"))
        print(f"[*] Phase 1: Profiling {len(raw_files)} datasets ({_backend.mode.upper()} Backend)...")
        for f_path in raw_files:
            base_name = os.path.basename(f_path).replace("_raw.csv", "")
            if "synthetic" in base_name: continue
            try:
                with open(f_path, 'r', encoding='utf-8') as f:
                    first_line = f.readline(); f.seek(0)
                    delim = ';' if ';' in first_line else ('\t' if '\t' in first_line else ',')
                    reader = csv.DictReader(f, delimiter=delim); headers = reader.fieldnames
                    records, numeric_data = [], []
                    for row in reader:
                        processed_row, numeric_row = {}, []
                        for h in headers:
                            val = row[h]
                            try:
                                num_val = float(val) if "." in val else int(val)
                                processed_row[h] = num_val; numeric_row.append(num_val)
                            except: processed_row[h] = val
                        records.append(processed_row)
                        if numeric_row: numeric_data.append(numeric_row)
                X = np.array(numeric_data)
                if X.size == 0: continue
                signal = X[:, np.argmax(np.var(X, axis=0))]
                report = extract_all_features(X=X, ts=signal)
                profile = {"metadata": {"source": os.path.basename(f_path), "total_samples": len(records), "headers": headers},
                           "structure": {"primitive_id": PRIMITIVE_ID_DATA_RECOVERY, "data_quanta": records, "analysis_report": report}}
                with open(os.path.join(DATA_DIR, f"{base_name}_morphic_profile.json"), 'w') as j:
                    json.dump(profile, j, indent=4, ensure_ascii=False)
                self.profiles[base_name] = profile; print(f"    - [SUCCESS] {base_name}")
            except Exception as e: print(f"    - [ERROR] {base_name}: {e}")

    def run_optimization(self):
        print(f"[*] Phase 2: Optimizing Primitives (Hurst, MF, Entropy, Var)...")
        results = []
        for name, profile in self.profiles.items():
            target = profile["structure"]["analysis_report"]; n = profile["metadata"]["total_samples"]
            def obj(p):
                s = generate_primitive_signal(n, p); rep = extract_all_features(ts=s)
                keys = ["hurst", "fractal_dim", "entropy", "var", "mf_width", "mf_singularity"]
                return sum((2.0 if k.startswith("mf_") else 1.0 if k != "var" else 0.1) * (target.get(k,0) - rep.get(k,0))**2 for k in keys)
            
            mu_init = 100
            res = minimize(obj, [mu_init, np.sqrt(target.get("var",100)), target.get("hurst", 0.7), 0], 
                           method='Nelder-Mead', options={'maxiter': 100})
            best = res.x; synth_s = generate_primitive_signal(n, best); rep_s = extract_all_features(ts=synth_s)
            pd.DataFrame({"Value": synth_s}).to_csv(os.path.join(DATA_DIR, f"synthetic_{name}_raw.csv"), index=False)
            results.append({"Dataset": name, "Mean": best[0], "Std": best[1], "Hurst_Param": best[2], "Trend_Param": best[3],
                            "Hurst_Match": rep_s.get("hurst"), "Hurst_Target": target.get("hurst"),
                            "Fractal_Match": rep_s.get("fractal_dim"), "Fractal_Target": target.get("fractal_dim")})
            print(f"    - [MODEL] {name}: H={best[2]:.4f}, Std={best[1]:.2f}")
        pd.DataFrame(results).to_csv(OUTPUT_REPORT, index=False)

    def run_visualization(self):
        print(f"[*] Phase 3: Generating Professional Reports (Rank-Normalized Space)...")
        df_rep = pd.read_csv(OUTPUT_REPORT)
        
        # 1. Character Map (Hurst vs Std) - Remains original space for physical meaning
        plt.figure(figsize=(12, 10))
        plt.scatter(df_rep['Hurst_Param'], df_rep['Std'], s=200, c=df_rep['Hurst_Param'], cmap='viridis', alpha=0.7, edgecolors='k')
        for i, row in df_rep.iterrows(): plt.annotate(row['Dataset'], (row['Hurst_Param'], row['Std']), xytext=(8,4), textcoords='offset points', fontweight='bold', fontsize=11)
        plt.axvline(x=0.5, color='r', linestyle='--', alpha=0.5); plt.text(0.48, plt.ylim()[1]*0.9, "Random (White Noise)", rotation=90, color='r', fontsize=10)
        plt.axvline(x=0.75, color='g', linestyle='--', alpha=0.5); plt.text(0.76, plt.ylim()[1]*0.9, "Strong Persistence", rotation=90, color='g', fontsize=10)
        plt.title("Character Map of Natural Logic Primitives (Model Comparison)", fontsize=16)
        plt.xlabel("Memory Strength (Hurst H)", fontsize=12); plt.ylabel("System Energy (Sigma)", fontsize=12); plt.grid(True, linestyle=':', alpha=0.6)
        plt.tight_layout(); plt.savefig(CHARACTER_MAP, dpi=300); plt.close()

        # 2. Similarity Map (PCA on RANK-NORMALIZED Full Feature Space)
        data_list, names = [], []
        for name, profile in self.profiles.items():
            rep = profile["structure"]["analysis_report"]; names.append(name)
            data_list.append({k: v for k, v in rep.items() if isinstance(v, (int, float))})
        df_f = pd.DataFrame(data_list, index=names).fillna(0)
        
        # APPLY RANK NORMALIZATION (CRITICAL IMPROVEMENT for feature fairness)
        df_f_ranked = rank_normalize(df_f)
        
        X_scaled = StandardScaler().fit_transform(df_f_ranked)
        pca = PCA(n_components=2); X_2d = pca.fit_transform(X_scaled)
        
        plt.figure(figsize=(14, 10))
        plt.scatter(X_2d[:, 0], X_2d[:, 1], s=150, alpha=0.7, edgecolors='k')
        for i, name in enumerate(df_f.index): plt.annotate(name, (X_2d[i, 0], X_2d[i, 1]), xytext=(5, 2), textcoords='offset points', fontsize=10)
        plt.title("Geometric Similarity Map of Nature Observations (Rank-Normalized Space)", fontsize=15)
        plt.xlabel(f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)"); plt.ylabel(f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)")
        plt.grid(True, linestyle='--', alpha=0.6); plt.savefig(SIMILARITY_MAP, dpi=300, bbox_inches='tight'); plt.close()
        
        print("\n[*] Top 3 'Persistent' Models:"); print(df_rep.sort_values('Hurst_Param', ascending=False)[['Dataset', 'Hurst_Param']].head(3).to_string(index=False))
        print("\n[*] Top 3 'Dynamic' Models:"); print(df_rep.sort_values('Std', ascending=False)[['Dataset', 'Std']].head(3).to_string(index=False))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PKGF Master Pipeline")
    parser.add_argument("--backend", type=str, choices=["python", "fortran"], default="python",
                        help="Mathematical backend to use (default: python)")
    args = parser.parse_args()

    master = PKGFMasterPipeline(backend_mode=args.backend)
    master.run_profiling(); master.run_optimization(); master.run_visualization()
    print(f"\n[SUCCESS] Pipeline Executed using {args.backend.upper()} backend.")
