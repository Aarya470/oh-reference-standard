import json, numpy as np, warnings
warnings.filterwarnings("ignore")
import importlib.util
spec=importlib.util.spec_from_file_location("rr","/sessions/amazing-sleepy-goldberg/mnt/outputs/run_regression.py")
rr=importlib.util.module_from_spec(spec); spec.loader.exec_module(rr)

def data():
    OUT="/sessions/amazing-sleepy-goldberg/mnt/outputs"
    rows=[r for r in json.load(open(f"{OUT}/pretilt_features.json")) if r.get("delta_SBP") is not None]
    keep=sorted({k for r in rows for k in r if k not in rr.META and not k.startswith("DB1ONLY")})
    keep=[k for k in keep if sum(1 for r in rows if isinstance(r.get(k),(int,float)) and np.isfinite(r.get(k)))>=0.9*len(rows)]
    X=np.array([[float(r.get(k)) if isinstance(r.get(k),(int,float)) and np.isfinite(r.get(k)) else np.nan for k in keep] for r in rows])
    y=np.array([r["delta_SBP"] for r in rows],float)
    g=np.array([r["subject"] for r in rows])
    return rows, keep, X, y, g, rr
