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

    def _find_column(self, columns, candidates):
        """Finds column name (case-insensitive) and returns (Name, Index)."""
        # 1. Exact match
        for idx, col in enumerate(columns):
            if str(col).lower().strip() in [c.lower() for c in candidates]:
                return col, idx
        # 2. Partial match
        for idx, col in enumerate(columns):
            for cand in candidates:
                if cand.lower() in str(col).lower():
                    return col, idx
        return None, None

    def preprocess_trajectory(self, df_raw):
        # WORK ON A COPY to avoid messing up original headers
        df = df_raw.copy()
        
        # Clean headers for internal processing ONLY
        df.columns = [str(c).strip() for c in df.columns]
        cols = df.columns
        
        # --- SMART COLUMN DETECTION ---
        track_candidates = ['Trajectory', 'Track ID', 'TrackID', 'Track', 'Spot ID', 'Particle ID']
        track_col, _ = self._find_column(cols, track_candidates)

        frame_candidates = ['Frame', 'Frame ID', 'Slice', 'Time', 't']
        frame_col, _ = self._find_column(cols, frame_candidates)

        x_candidates = ['x', 'xpx', 'Position X', 'X (um)', 'X (px)']
        x_col, _ = self._find_column(cols, x_candidates)
        
        y_candidates = ['y', 'ypx', 'Position Y', 'Y (um)', 'Y (px)']
        y_col, _ = self._find_column(cols, y_candidates)

        if not all([track_col, frame_col, x_col, y_col]):
            return None, None, None, f"Missing columns. Found: {track_col}, {frame_col}"

        # --- EXTRACT DATA ---
        xs_list, ys_list, ids_list = [], [], []

        for tid, g in df.groupby(track_col):
            g = g.sort_values(frame_col)
            
            # Normalize Time
            t_raw = g[frame_col].to_numpy().astype(float)
            t = t_raw - t_raw.min()
            
            if len(t) < 3 or t.max() == 0: continue

            t /= t.max()
            t_uniform = np.linspace(0, 1, self.target_frames)
            
            try:
                # Interpolate
                x_vals = g[x_col].to_numpy().astype(float)
                y_vals = g[y_col].to_numpy().astype(float)
                
                xs_list.append(np.interp(t_uniform, t, x_vals))
                ys_list.append(np.interp(t_uniform, t, y_vals))
                ids_list.append(tid)
            except: continue

        if not xs_list: 
            return None, None, [], "0 valid tracks found (check lengths)."

        X_arr = np.array(xs_list)
        X_in = np.diff(X_arr, axis=1)[:, :, np.newaxis]
        
        # Return the INPUT df (copy) just for column name reference if needed
        return X_in, ids_list, df, "Success"

    def run_inference(self, file_path, filter_type="All"):
        try:
            # Read CSV
            df_raw = pd.read_csv(file_path)
            if df_raw.empty: return None, 0, 0, "File is empty."

            # 1. Preprocess (Pass raw, it makes a copy)
            X_in, track_ids, df_clean_ref, msg = self.preprocess_trajectory(df_raw)
            
            if X_in is None: return None, 0, 0, msg

            if self.model is None: return None, 0, 0, "Model not loaded."
                
            # 2. Predict
            probs = self.model.predict(X_in, verbose=0)
            labels_map = ["Brownian", "FBM", "CTRW"]
            pred_labels = [labels_map[i] for i in probs.argmax(axis=1)]

            # 3. Create Results
            results = pd.DataFrame({"Trajectory": track_ids, "MoNet_Label": pred_labels})
            original_count = len(track_ids)
            
            # 4. Filter
            if filter_type != "All":
                results = results[results["MoNet_Label"] == filter_type]
            
            if results.empty:
                return pd.DataFrame(), original_count, 0, f"No {filter_type} tracks."

            valid_ids = results["Trajectory"].unique()
            
            # --- CRITICAL: FILTER THE ORIGINAL DATAFRAME (PRESERVING HEADERS) ---
            
            # We need to find which column in df_raw corresponds to the Track ID
            # We use the cleaned reference to find the index, then map to raw.
            clean_track_col = next(c for c in df_clean_ref.columns if str(c).strip().lower() in ['trajectory', 'track id', 'trackid', 'track'])
            col_idx = df_clean_ref.columns.get_loc(clean_track_col)
            raw_track_col = df_raw.columns[col_idx] # This has the original spaces/formatting
            
            # Filter
            original_df_filtered = df_raw[df_raw[raw_track_col].isin(valid_ids)].copy()

            # --- CRITICAL FIX: FORCE INTEGERS ---
            # If pandas read "1" as "1.0", convert it back to "1" to satisfy MPTHub
            try:
                if original_df_filtered[raw_track_col].dtype == float:
                     original_df_filtered[raw_track_col] = original_df_filtered[raw_track_col].astype(int)
                     
                # Do the same for Frame column if possible
                clean_frame_col = next(c for c in df_clean_ref.columns if str(c).strip().lower() in ['frame', 'frame id', 't'])
                frame_idx = df_clean_ref.columns.get_loc(clean_frame_col)
                raw_frame_col = df_raw.columns[frame_idx]
                
                if original_df_filtered[raw_frame_col].dtype == float:
                    original_df_filtered[raw_frame_col] = original_df_filtered[raw_frame_col].astype(int)
            except:
                pass # If conversion fails (e.g. strings), leave it alone

            return original_df_filtered, original_count, len(results), "Success"

        except Exception as e:
            return None, 0, 0, f"Error: {str(e)}"