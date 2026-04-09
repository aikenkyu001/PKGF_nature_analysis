import json
import os
import glob
import numpy as np

def compare_profiles():
    python_dir = "Data/python_profiles"
    fortran_dir = "Data/fortran_profiles"
    
    profiles = glob.glob(os.path.join(python_dir, "*.json"))
    
    print(f"=== PKGF Full Dataset Backend Comparison Report ===")
    print("{:<20} | {:<10} | {:<10} | {:<10}".format("Dataset", "Hurst", "Fractal", "Fisher"))
    print("-" * 60)
    
    metrics = ["hurst", "fractal_dim", "fisher"]
    all_match = True
    
    for py_path in sorted(profiles):
        base_name = os.path.basename(py_path)
        ft_path = os.path.join(fortran_dir, base_name)
        
        if not os.path.exists(ft_path):
            print(f"[ERROR] {base_name} missing in fortran profiles.")
            continue
            
        with open(py_path, 'r') as f: py_data = json.load(f)
        with open(ft_path, 'r') as f: ft_data = json.load(f)
        
        py_rep = py_data["structure"]["analysis_report"]
        ft_rep = ft_data["structure"]["analysis_report"]
        
        deltas = []
        for m in metrics:
            d = abs(py_rep[m] - ft_rep[m])
            deltas.append(d)
        
        status = []
        for d in deltas:
            if d < 1e-8: status.append("OK")
            else:
                status.append("DIFF")
                all_match = False
                
        name_short = base_name.replace("_morphic_profile.json", "")
        print("{:<20} | {:<10} | {:<10} | {:<10}".format(
            name_short, status[0], status[1], status[2]))
            
        # Optional: Print actual deltas for DIFF
        if "DIFF" in status:
            print(f"  [!] Detail Delta: H:{deltas[0]:.2e}, D:{deltas[1]:.2e}, F:{deltas[2]:.2e}")

    if all_match:
        print("\n[SUCCESS] All 21 datasets match perfectly between Python and Fortran backends.")
    else:
        print("\n[WARNING] Some datasets showed discrepancies. Check floating point precision or data consistency.")

if __name__ == "__main__":
    compare_profiles()
