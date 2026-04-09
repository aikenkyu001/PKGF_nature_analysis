import numpy as np
import pandas as pd
import os
import sys

# Ensure we can import from the Scripts directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pkgf_master_pipeline import MathBackend, extract_all_features

def run_validation():
    print("=== PKGF Math Backend Cross-Validation ===")
    
    # 1. Initialize both backends
    try:
        py_backend = MathBackend(mode="python")
        ft_backend = MathBackend(mode="fortran")
    except Exception as e:
        print(f"[ERROR] Failed to initialize backends: {e}")
        return

    if ft_backend.mode != "fortran":
        print("[ERROR] Fortran backend failed to load. Validation aborted.")
        print("        Ensure you have compiled the library:")
        print("        gfortran -O3 -shared -fPIC -o Scripts/pkgf_math_core.so Scripts/pkgf_math_core.f90")
        return

    # 2. Load Test Data (Nile dataset is a good benchmark)
    raw_file = "Data/nile_raw.csv"
    if not os.path.exists(raw_file):
        print(f"[ERROR] Test data {raw_file} not found.")
        return
        
    df = pd.read_csv(raw_file)
    X = df.select_dtypes(include=[np.number]).values
    signal = X[:, np.argmax(np.var(X, axis=0))]
    signal = (signal - np.mean(signal)) / (np.std(signal) + 1e-12)

    print(f"[*] Testing on: {raw_file} (N={len(signal)})")

    # 3. Targeted Comparison
    metrics = [
        ("Hurst Exponent", lambda b: b.hurst(signal)),
        ("Fractal Dimension", lambda b: b.fractal_dim(signal)),
        ("Fisher Information", lambda b: b.fisher(signal, bins=32))
    ]

    print("\n{:<20} | {:<12} | {:<12} | {:<10}".format("Metric", "Python", "Fortran", "Delta"))
    print("-" * 62)

    for name, func in metrics:
        val_py = func(py_backend)
        val_ft = func(ft_backend)
        delta = abs(val_py - val_ft)
        status = "MATCH" if delta < 1e-8 else "DIFF"
        print("{:<20} | {:<12.6f} | {:<12.6f} | {:<10.2e} [{}]".format(name, val_py, val_ft, delta, status))

    # 4. High-level Feature Extraction Comparison
    print("\n[*] Full Feature Extraction Integration Test...")
    # Temporarily override global backend for extraction tests
    import pkgf_master_pipeline
    
    pkgf_master_pipeline._backend = py_backend
    feats_py = extract_all_features(ts=signal)
    
    pkgf_master_pipeline._backend = ft_backend
    feats_ft = extract_all_features(ts=signal)

    # Compare key keys
    keys_to_check = ["hurst", "fractal_dim", "fisher"]
    all_pass = True
    for k in keys_to_check:
        d = abs(feats_py[k] - feats_ft[k])
        if d > 1e-8:
            all_pass = False
            print(f"  [!] Mismatch in integrated extraction for '{k}': delta={d:.2e}")
    
    if all_pass:
        print("  [SUCCESS] All core features match in full extraction pipeline.")

if __name__ == "__main__":
    run_validation()
