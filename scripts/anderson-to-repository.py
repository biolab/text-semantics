"""
This script generates text and metadata files for the Text semantics repository
for Anderson
"""

import pandas as pd
import os
import unicodedata as ud

import yaml

save_dir = "grimmove-pravljice"

df = pd.read_csv("grimmove-pravljice.csv")
print(df.columns)

os.mkdir(save_dir)

for i, row in df.iterrows():
    file_name = ud.normalize('NFKD', row["naslov"]).encode('ascii', 'ignore').decode("utf-8")
    file_name = file_name.lower().replace(" ", "-").replace(",", "").replace(".", "")
    text_file = f"{file_name}.txt"
    with open(os.path.join(save_dir, text_file), "w") as f:
        f.write(row["vsebina"])

    row = row.to_dict()
    row["Text file"] = text_file
    row.pop("vsebina")

    with open(os.path.join(save_dir, f"{file_name}.yaml"), "w") as f:
        yaml.dump(row, f, default_flow_style=False)