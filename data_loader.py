import json
import pandas as pd

def load_positions(path="positions.json"):
    with open(path, "r") as f:
        data = json.load(f)

    global_df = pd.DataFrame(data["global"])
    mexico_df = pd.DataFrame(data["mexico"])

    df = pd.concat([global_df, mexico_df], ignore_index=True)

    df["costo_total"] = df["costo_promedio"] * df["titulos"]
    return df
