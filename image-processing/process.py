import cv2
import numpy as np
import os
import json
import shutil
import argparse
import re
from sklearn.cluster import KMeans

# CONFIG
INPUT_DIR = "raw_assets"
OUTPUT_DIR = "app_assets"
INITIAL_K = 24       
MERGE_THRESHOLD = 40 
BACKGROUND_ID = 255  
LINE_ID = 254        

# === CRITICAL UPDATES ===
# 1. Bumped from 25 -> 50. 
# This ensures those thick Owl outlines are treated as "Walls" (Lines), 
# not "Rooms" (Paintable Regions). The '1's will disappear.
OUTLINE_THICKNESS_THRESHOLD = 50

# 2. Bumped from 25 -> 30.
# Since lines are thicker, we need a slightly wider 'Reach' to group 
# the colors on either side of them.
NEIGHBOR_GAP = 30  

# 3. Standard settings
MIN_REGION_AREA = 50
DESPECKLE_SIZE = 5

def rgb_to_hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2]))

def color_distance(c1, c2):
    return np.sqrt(np.sum((c1 - c2) ** 2))

def get_luminance(rgb):
    return 0.299*rgb[0] + 0.587*rgb[1] + 0.114*rgb[2]

def get_pole_of_inaccessibility(mask):
    dist_transform = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    _, max_val, _, max_loc = cv2.minMaxLoc(dist_transform)
    return max_loc[0], max_loc[1], max_val 

# --- GROUPING LOGIC ---
def group_neighboring_regions(map_img, color_idx, min_area, neighbor_gap):
    """
    Groups regions by simulating a 'flood' that bridges gaps (black lines).
    """
    mask = np.uint8(map_img == color_idx) * 255
    
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    original_regions = []
    
    for i in range(1, num_labels):
        if stats[i, cv2.CC_STAT_AREA] >= min_area:
            original_regions.append(i) 

    if not original_regions:
        return []

    # Dilate mask to bridge gaps
    kernel_size = max(3, neighbor_gap)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    bridged_mask = cv2.dilate(mask, kernel)
    
    num_groups, bridged_labels, _, _ = cv2.connectedComponentsWithStats(bridged_mask, connectivity=8)
    
    groups = {} 
    for orig_label_id in original_regions:
        ys, xs = np.where(labels == orig_label_id)
        if len(ys) == 0: continue
        
        group_id = bridged_labels[ys[0], xs[0]]
        if group_id == 0: continue

        if group_id not in groups:
            groups[group_id] = []
        
        component_mask = np.uint8(labels == orig_label_id) * 255
        area = stats[orig_label_id, cv2.CC_STAT_AREA]
        
        groups[group_id].append({
            'mask': component_mask,
            'area': area
        })
        
    result_groups = []
    for gid, region_list in groups.items():
        total_area = sum(r['area'] for r in region_list)
        # Label placement logic
        largest_region = max(region_list, key=lambda x: x['area'])
        cx, cy, _ = get_pole_of_inaccessibility(largest_region['mask'])
        
        result_groups.append({
            'regions': region_list,
            'best_label_pos': (cx, cy),
            'total_area': total_area
        })
        
    return result_groups

def remove_small_regions(map_img, min_area):
    h, w = map_img.shape
    unique_ids = np.unique(map_img)
    total_cleaned = 0
    
    for uid in unique_ids:
        if uid == BACKGROUND_ID: continue
        mask = np.uint8(map_img == uid) * 255
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
        
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            if area < min_area:
                blob_mask = np.uint8(labels == i) * 255
                dilated = cv2.dilate(blob_mask, np.ones((3,3), np.uint8))
                neighbor_mask = cv2.bitwise_xor(dilated, blob_mask)
                neighbors = map_img[neighbor_mask > 0]
                
                if len(neighbors) > 0:
                    counts = np.bincount(neighbors)
                    dominant_neighbor = np.argmax(counts)
                    map_img[blob_mask > 0] = dominant_neighbor
                    total_cleaned += 1
    return map_img

def process_level(filename):
    print(f"Processing {filename}...")
    base_name = os.path.splitext(filename)[0]
    
    img_path = os.path.join(INPUT_DIR, filename)
    vid_path = os.path.join(INPUT_DIR, base_name + ".mp4") 
    save_path = os.path.join(OUTPUT_DIR, base_name)
    
    if not os.path.exists(save_path): os.makedirs(save_path)

    img = cv2.imread(img_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    print("   - Ironing gradients...")
    img = cv2.pyrMeanShiftFiltering(img, sp=40, sr=80)
    img = cv2.bilateralFilter(img, 9, 75, 75) 

    pixels = img.reshape((-1, 3))
    kmeans = KMeans(n_clusters=INITIAL_K, random_state=42, n_init=10)
    kmeans.fit(pixels)
    centers = kmeans.cluster_centers_
    labels = kmeans.labels_
    
    print(f"   - K-Means: {INITIAL_K} colors.")

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

    print(f"   - Merged to {len(final_centers)} colors.")

    new_labels = np.array([final_map_map[l] for l in labels])
    map_img = new_labels.reshape(img.shape[:2]).astype(np.uint8)
    
    print("   - Melting gaps...")
    kernel = np.ones((3,3), np.uint8) 
    map_img = cv2.morphologyEx(map_img, cv2.MORPH_CLOSE, kernel)
    map_img = cv2.medianBlur(map_img, DESPECKLE_SIZE) 

    # --- LINE DETECTION ---
    min_lum = 255
    darkest_idx = -1
    for idx, color in enumerate(final_centers):
        lum = get_luminance(color)
        if lum < min_lum:
            min_lum = lum
            darkest_idx = idx
            
    has_black_outline = False
    if min_lum < 50: 
        print(f"   - Analyzing Darkest Color (ID: {darkest_idx}, Lum: {min_lum:.1f})...")
        dark_mask = np.uint8(map_img == darkest_idx) * 255
        
        # Here is the magic: We try to 'Open' (Erode then Dilate) the black mask.
        # Only shapes THICKER than 50px will survive.
        # Everything else (your Owl lines) is subtracted and becomes a 'Line'.
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (OUTLINE_THICKNESS_THRESHOLD, OUTLINE_THICKNESS_THRESHOLD))
        paintable_dark_parts = cv2.morphologyEx(dark_mask, cv2.MORPH_OPEN, kernel)
        detected_lines = dark_mask - paintable_dark_parts
        
        num_l, labels_l, stats_l, _ = cv2.connectedComponentsWithStats(detected_lines, connectivity=8)
        cleaned_lines = np.zeros_like(detected_lines)
        for i in range(1, num_l):
            if stats_l[i, cv2.CC_STAT_AREA] > 20: 
                cleaned_lines[labels_l == i] = 255
        
        if np.count_nonzero(cleaned_lines) > 0:
            map_img[cleaned_lines > 0] = LINE_ID
            has_black_outline = True
            print(f"   - SUCCESS: Detected lines (thinner than {OUTLINE_THICKNESS_THRESHOLD}px).")
        else:
            print("   - WARNING: No lines detected.")

    map_img = remove_small_regions(map_img, MIN_REGION_AREA)
    
    h, w = map_img.shape[:2]
    mask = np.zeros((h+2, w+2), np.uint8)
    cv2.floodFill(map_img, mask, (0,0), BACKGROUND_ID, flags=4 | (255 << 8))
    cv2.floodFill(map_img, mask, (w-1, 0), BACKGROUND_ID, flags=4 | (255 << 8))
    cv2.floodFill(map_img, mask, (0, h-1), BACKGROUND_ID, flags=4 | (255 << 8))
    cv2.floodFill(map_img, mask, (w-1, h-1), BACKGROUND_ID, flags=4 | (255 << 8))

    lines = np.zeros_like(map_img)
    gradient = cv2.morphologyEx(map_img, cv2.MORPH_GRADIENT, np.ones((3,3), np.uint8))
    lines[gradient > 0] = 255 
    if has_black_outline:
        lines[map_img == LINE_ID] = 255

    lines_rgba = np.zeros((h, w, 4), dtype=np.uint8)
    lines_rgba[lines > 0] = [0, 0, 0, 255] 

    number_data = []
    palette = [rgb_to_hex(c) for c in final_centers]
    unique_ids = np.unique(map_img)

    total_regions = 0
    total_labels = 0

    print("   - Grouping neighbors and placing labels...")
    for color_idx in unique_ids:
        # SKIP lines and background
        if color_idx == BACKGROUND_ID or color_idx == LINE_ID:
            continue

        groups = group_neighboring_regions(map_img, color_idx, MIN_REGION_AREA, neighbor_gap=NEIGHBOR_GAP)

        for group in groups:
            total_regions += len(group['regions'])
            total_labels += 1

            cx, cy = group['best_label_pos']
            number_data.append({
                "number": int(color_idx + 1),
                "x": int(cx),
                "y": int(cy),
                "color_index": int(color_idx)
            })

    print(f"   - Consolidated {total_regions} regions into {total_labels} labels.")

    display_map = map_img.copy()
    if has_black_outline:
        display_map[display_map == LINE_ID] = darkest_idx
        
    clean_img_pixels = np.array([final_centers[l if l < len(final_centers) else 0] for l in display_map.flatten()])
    clean_img = clean_img_pixels.reshape(img.shape).astype(np.uint8)
    
    cv2.imwrite(os.path.join(save_path, "original.png"), cv2.cvtColor(clean_img, cv2.COLOR_RGB2BGR))
    cv2.imwrite(os.path.join(save_path, "lines.png"), lines_rgba)
    cv2.imwrite(os.path.join(save_path, "map.png"), map_img)
    
    debug_img = cv2.cvtColor(clean_img, cv2.COLOR_RGB2BGR)
    for item in number_data:
        cv2.putText(debug_img, str(item['number']), (item['x']-10, item['y']+5), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 4)
        cv2.putText(debug_img, str(item['number']), (item['x']-10, item['y']+5), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,0), 2)
        
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
        "background_id": BACKGROUND_ID,
        "line_id": LINE_ID
    }
    
    with open(os.path.join(save_path, "data.json"), 'w') as f:
        json.dump(level_data, f, indent=2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process paint-by-numbers images")
    parser.add_argument("--from", dest="start_from", type=int, default=1, help="Start from")
    args = parser.parse_args()

    if not os.path.exists(INPUT_DIR): os.makedirs(INPUT_DIR)
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

    def get_file_number(filename):
        match = re.match(r'^(\d+)', filename)
        return int(match.group(1)) if match else 0

    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    files = [f for f in files if get_file_number(f) >= args.start_from]
    files.sort(key=get_file_number)

    print(f"Processing {len(files)} files...")
    for f in files: process_level(f)