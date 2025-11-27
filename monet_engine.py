import os
import numpy as np
import pandas as pd
from tensorflow import keras

# Suppress TF logs
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

class MoNetEngine:
    def __init__(self):
        self.model = None
        self.target_frames = 300

    def load_model(self, model_path):
        try:
            self.model = keras.models.load_model(model_path, compile=False)
            return True, "Model loaded successfully."
        except Exception as e:
            return False, f"Error loading model: {str(e)}"

    def preprocess_trajectory(self, df):
        TRACK_ID_COL, FRAME_COL, X_COL, Y_COL = "Trajectory", "Frame", "x", "y"
        df.columns = [c.strip() for c in df.columns]
        
        xs_list, ys_list, ids_list = [], [], []

        for tid, g in df.groupby(TRACK_ID_COL):
            g = g.sort_values(FRAME_COL)
            t = (g[FRAME_COL] - g[FRAME_COL].min()).to_numpy().astype(float)
            if len(t) < 2 or t.max() == 0: continue

            t /= t.max()
            t_uniform = np.linspace(0, 1, self.target_frames)
            
            xs_list.append(np.interp(t_uniform, t, g[X_COL].to_numpy()))
            ys_list.append(np.interp(t_uniform, t, g[Y_COL].to_numpy()))
            ids_list.append(tid)

        if not xs_list: return None, None, [], []

        X_arr = np.array(xs_list)
        X_in = np.diff(X_arr, axis=1)[:, :, np.newaxis]
        
        return X_in, ids_list, df, len(ids_list)

    def run_inference(self, file_path, filter_type="All"):
        try:
            df_raw = pd.read_csv(file_path).dropna()
            
            # 1. Preprocess
            X_in, track_ids, original_df, original_count = self.preprocess_trajectory(df_raw)
            if X_in is None: return None, None, 0, "No valid trajectories."

            if self.model is None: return None, None, 0, "Model not loaded."
                
            # 2. Predict
            probs = self.model.predict(X_in, verbose=0)
            labels_map = ["Brownian", "FBM", "CTRW"]
            pred_labels = [labels_map[i] for i in probs.argmax(axis=1)]

            # 3. Create Results Mapping
            results = pd.DataFrame({"Trajectory": track_ids, "MoNet_Label": pred_labels})

            # 4. Filter
            if filter_type != "All":
                results = results[results["MoNet_Label"] == filter_type]
                valid_ids = results["Trajectory"].unique()
                original_df = original_df[original_df["Trajectory"].isin(valid_ids)]

            # Return: Filtered Raw Data, Original Count, Filtered Count
            return original_df, original_count, len(results), "Success"

        except Exception as e:
            return None, 0, 0, str(e)