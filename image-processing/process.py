import cv2
import numpy as np
import os
import json
import shutil
from sklearn.cluster import KMeans

# CONFIG
INPUT_DIR = "raw_assets"
OUTPUT_DIR = "app_assets"
INITIAL_K = 24       # Start high to catch details
MERGE_THRESHOLD = 40 # Increased to 40 to better merge similar shades (fix for your 21 colors issue)
MIN_REGION_AREA = 200 
BACKGROUND_ID = 255  # Special reserved ID for the unpaintable background

def rgb_to_hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2]))

def color_distance(c1, c2):
    return np.sqrt(np.sum((c1 - c2) ** 2))

def process_level(filename):
    print(f"Processing {filename}...")
    base_name = os.path.splitext(filename)[0]
    
    img_path = os.path.join(INPUT_DIR, filename)
    vid_path = os.path.join(INPUT_DIR, base_name + ".mp4") 
    save_path = os.path.join(OUTPUT_DIR, base_name)
    
    if not os.path.exists(save_path): os.makedirs(save_path)

    # 1. Load & Smooth
    img = cv2.imread(img_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = cv2.bilateralFilter(img, 9, 75, 75) 

    # 2. K-Means Clustering
    pixels = img.reshape((-1, 3))
    kmeans = KMeans(n_clusters=INITIAL_K, random_state=42, n_init=10)
    kmeans.fit(pixels)
    centers = kmeans.cluster_centers_
    labels = kmeans.labels_

    # 3. Smart Merge (Reduce Palette)
    map_map = {i: i for i in range(INITIAL_K)} 
    sorted_indices = np.argsort([np.sum(c) for c in centers])
    
    final_centers = []
    final_map_map = {} 
    processed_indices = set()
    new_idx_counter = 0
    
    for i in sorted_indices:
        if i in processed_indices: continue
        current_center = centers[i]
        final_centers.append(current_center)
        final_map_map[i] = new_idx_counter
        processed_indices.add(i)
        
        for j in sorted_indices:
            if j in processed_indices: continue
            dist = color_distance(current_center, centers[j])
            if dist < MERGE_THRESHOLD:
                final_map_map[j] = new_idx_counter
                processed_indices.add(j)
        new_idx_counter += 1

    print(f"   - Palette reduced to {len(final_centers)} colors.")

    # 4. Apply Merged Map
    new_labels = np.array([final_map_map[l] for l in labels])
    map_img = new_labels.reshape(img.shape[:2]).astype(np.uint8)
    
    # ============================================================
    # NEW STEP: BACKGROUND REMOVAL (The Flood Fill Fix)
    # ============================================================
    # We assume the top-left pixel (0,0) is background.
    # We floodFill the 'map_img' with the value 255 (BACKGROUND_ID)
    # This separates the "White Background" from "White Eyes".
    
    # Create a mask for floodFill (needs to be 2 pixels larger than image)
    h, w = map_img.shape[:2]
    mask = np.zeros((h+2, w+2), np.uint8)
    
    # Flood fill starts at (0,0) and turns connected area to 255
    # flags=4 means check only adjacent pixels, (255 << 8) sets fill value
    cv2.floodFill(map_img, mask, (0,0), BACKGROUND_ID, flags=4 | (255 << 8))
    
    # Optional: Fill other corners too just in case (e.g. if hair touches top edge)
    cv2.floodFill(map_img, mask, (w-1, 0), BACKGROUND_ID, flags=4 | (255 << 8))
    cv2.floodFill(map_img, mask, (0, h-1), BACKGROUND_ID, flags=4 | (255 << 8))
    cv2.floodFill(map_img, mask, (w-1, h-1), BACKGROUND_ID, flags=4 | (255 << 8))

    print(f"   - Background masked (ID: {BACKGROUND_ID})")

    # ============================================================

    palette = [rgb_to_hex(c) for c in final_centers]

    # 5. Edge Detection (Lines)
    # Edges between Subject and Background (255) will still be drawn (Good!)
    lines = np.zeros_like(map_img)
    gradient = cv2.morphologyEx(map_img, cv2.MORPH_GRADIENT, np.ones((3,3), np.uint8))
    lines[gradient > 0] = 255 
    
    lines_rgba = np.zeros((h, w, 4), dtype=np.uint8)
    lines_rgba[lines > 0] = [0, 0, 0, 255] 

    # 6. Number Placement
    number_data = []
    
    # Important: We only iterate through VALID colors, skipping 255
    unique_ids = np.unique(map_img)
    
    for color_idx in unique_ids:
        if color_idx == BACKGROUND_ID:
            continue # Skip the background!
            
        mask = np.uint8(map_img == color_idx) * 255
        num_labels, lbls, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
        
        for i in range(1, num_labels): 
            area = stats[i, cv2.CC_STAT_AREA]
            if area > MIN_REGION_AREA:
                cx, cy = int(centroids[i][0]), int(centroids[i][1])
                if mask[cy, cx] == 255:
                    number_data.append({
                        "number": int(color_idx + 1), # Use int() to fix JSON serialization
                        "x": cx, 
                        "y": cy,
                        "color_index": int(color_idx)
                    })

    # 7. Save Assets (Debug Preview Included)
    clean_img_pixels = np.array([final_centers[l if l < len(final_centers) else 0] for l in new_labels])
    clean_img = clean_img_pixels.reshape(img.shape).astype(np.uint8)
    
    # Make background white in the "Original" preview if you want, 
    # but the palette logic handles the coloring.
    
    cv2.imwrite(os.path.join(save_path, "original.png"), cv2.cvtColor(clean_img, cv2.COLOR_RGB2BGR))
    cv2.imwrite(os.path.join(save_path, "lines.png"), lines_rgba)
    cv2.imwrite(os.path.join(save_path, "map.png"), map_img)
    
    # Debug Preview
    debug_img = cv2.cvtColor(clean_img, cv2.COLOR_RGB2BGR)
    for item in number_data:
        cv2.putText(debug_img, str(item['number']), (item['x'], item['y']), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 3)
        cv2.putText(debug_img, str(item['number']), (item['x'], item['y']), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
    cv2.imwrite(os.path.join(save_path, "debug_preview.png"), debug_img)

    has_video = False
    if os.path.exists(vid_path):
        shutil.copy(vid_path, os.path.join(save_path, "reward.mp4"))
        has_video = True
    
    level_data = {
        "id": base_name,
        "palette": palette,
        "numbers": number_data,
        "dimensions": {"w": w, "h": h},
        "has_reward": has_video,
        "background_id": BACKGROUND_ID
    }
    
    with open(os.path.join(save_path, "data.json"), 'w') as f:
        json.dump(level_data, f, indent=2)

if not os.path.exists(INPUT_DIR): os.makedirs(INPUT_DIR)
if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
for f in files: process_level(f)
