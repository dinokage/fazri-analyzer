# backend/scripts/debug_columns.py
import pandas as pd
from pathlib import Path

data_dir = Path(__file__).parent.parent / "filtered"

print("📊 Dataset Column Analysis")
print("="*60)

datasets = {
    'library': 'library_checkouts.csv',
    'lab bookings': 'lab_bookings.csv',
    'helpdesk': 'helpdesk.csv',
    'cctv': 'cctv_frames.csv',
}

for name, filename in datasets.items():
    filepath = data_dir / filename
    if filepath.exists():
        df = pd.read_csv(filepath)
        print(f"\n{name.upper()}:")
        print(f"  Columns: {df.columns.tolist()}")
        print(f"  Shape: {df.shape}")
        print(f"  First row:")
        for col in df.columns:
            print(f"    {col}: {df[col].iloc[0]}")
    else:
        print(f"\n{name.upper()}: FILE NOT FOUND")