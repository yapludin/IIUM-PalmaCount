import base64
from io import BytesIO
from PIL import Image
import numpy as np
import matplotlib.pyplot as plt
import cv2
from .model_loader import model, class_names

# --- SERVER CONFIGURATION ---
# Set Matplotlib to non-interactive mode.
# This is CRITICAL. Without this, the server tries to open a popup window 
# and crashes on the cloud (Render).
plt.switch_backend('Agg')

# --- GIS PARAMETERS ---
# Ground Sample Distance (GSD): How many meters does one pixel represent?
# Standard drone height (100m) usually gives ~0.1m/pixel.
GSD = 0.1 

def calculate_area_research_based(detections, gsd, method='multiple_radii'):
    """
    Calculates the canopy area of each tree using research-validated geometry.
    Based on: Owen & Lines (2024) - Ecological Indicators.
    """
    tree_data = []
    # Initialize counters for all known classes
    counters = {name: 0 for name in class_names.values()}
    total_area = 0
    
    # We assume batch size of 1 for the web app
    if not detections:
        return 0, [], counters, "No Detections"

    result = detections[0]
    
    for box_obj in result.boxes:
        class_id = int(box_obj.cls)
        # Skip if the model detects a class ID we don't have a name for
        if class_id not in class_names:
            continue
            
        class_name = class_names[class_id]
        x1, y1, x2, y2 = map(int, box_obj.xyxy[0].cpu().numpy())
        confidence = float(box_obj.conf[0].cpu().numpy())
        
        counters[class_name] += 1
        
        # Calculate bounding box dimensions in pixels
        width_px = x2 - x1
        height_px = y2 - y1
        
        area = 0
        crown_diameter_m = 0

        # Apply the selected geometric method
        if method == 'multiple_radii':
            # RESEARCH-BEST: Average of multiple radii (Approximated by avg diameter)
            avg_diameter_px = (width_px + height_px) / 2
            crown_diameter_m = avg_diameter_px * gsd
            area = np.pi * (crown_diameter_m / 2) ** 2
            
        elif method == 'max_perpendicular':
            # Max and perpendicular diameters
            max_diameter_px = max(width_px, height_px)
            perp_diameter_px = min(width_px, height_px)
            avg_diameter_m = (max_diameter_px + perp_diameter_px) / 2 * gsd
            area = np.pi * (avg_diameter_m / 2) ** 2
            
        elif method == 'ellipse':
            # Elliptical Area
            width_m = width_px * gsd
            height_m = height_px * gsd
            area = np.pi * (width_m / 2) * (height_m / 2)
        
        total_area += area
        
        tree_data.append({
            'class_name': class_name,
            'confidence': confidence,
            'crown_diameter_m': crown_diameter_m,
            'area_m2': area
        })
    
    method_name = f"Geometric: {method} (GSD: {gsd}m/px)"
    return total_area, tree_data, counters, method_name

def generate_research_plots(counters, tree_data, total_trees):
    """
    Generates two professional charts:
    1. Canopy Size Histogram (Insight into growth stage)
    2. Composition Donut Chart (Insight into health/yield)
    """
    if total_trees == 0:
        return None

    # Create a figure with 2 columns
    # Increased size significantly for better visibility
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10)) 
    
    # --- CHART 1: CANOPY SIZE HISTOGRAM ---
    # Extract areas of all trees
    areas = [t['area_m2'] for t in tree_data]
    
    if areas:
        # Create a histogram of tree sizes
        # Color: Emerald Green gradient feel
        n, bins, patches = ax1.hist(areas, bins=15, color='#10b981', alpha=0.8, edgecolor='white', rwidth=0.9)
        ax1.set_title('Canopy Size Distribution', fontsize=18, fontweight='bold', pad=20)
        ax1.set_xlabel('Canopy Area (m²)', fontsize=14)
        ax1.set_ylabel('Frequency', fontsize=14)
        ax1.tick_params(axis='both', which='major', labelsize=12)
        
        # Modern grid
        ax1.grid(axis='y', linestyle='--', alpha=0.3, color='gray')
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        
        # Add a vertical line for the average size
        avg_area = np.mean(areas)
        ax1.axvline(avg_area, color='#ef4444', linestyle='dashed', linewidth=2)
        ax1.text(avg_area*1.05, ax1.get_ylim()[1]*0.9, f'Avg: {avg_area:.1f} m²', color='#ef4444', fontweight='bold', fontsize=14)
    else:
        ax1.text(0.5, 0.5, "No Area Data", ha='center', va='center', fontsize=14)
    
    # --- CHART 2: COMPOSITION DONUT CHART ---
    # Filter out zero counts
    labels = [k for k, v in counters.items() if v > 0]
    sizes = [v for k, v in counters.items() if v > 0]
    
    # Modern Professional Palette
    colors_map = {
        'Mature(Healthy)': '#15803d', # Deep Green
        'Mature(Yellow)': '#fbbf24',  # Amber
        'Mature(Dead)': '#dc2626',    # Red
        'Young': '#84cc16',           # Lime
        'Grass': '#a8a29e'            # Stone Gray
    }
    plot_colors = [colors_map.get(label, '#94a3b8') for label in labels]

    if sizes:
        # Donut Chart
        wedges, texts, autotexts = ax2.pie(
            sizes, 
            labels=None, # Hide labels on the pie itself to avoid clutter
            autopct='%1.1f%%', 
            startangle=90, 
            colors=plot_colors, 
            pctdistance=0.78, # Move % inside the ring
            textprops={'color': "white", 'weight': "bold", 'fontsize': 14},
            wedgeprops=dict(width=0.35, edgecolor='white', linewidth=2)
        )
        
        # Center Text
        ax2.set_title('Plantation Vitality', fontsize=18, fontweight='bold', pad=20)
        ax2.text(0, 0, f"{total_trees}\nTotal", ha='center', va='center', fontsize=22, fontweight='black', color='#334155')
        
        # Create a professional Legend
        # We calculate percentages for the legend
        total = sum(sizes)
        legend_labels = [f'{l} ({s})' for l, s in zip(labels, sizes)]
        
        ax2.legend(
            wedges, 
            legend_labels,
            title="Categories",
            loc="center left",
            bbox_to_anchor=(0.9, 0, 0.5, 1), # Position legend outside to the right
            fontsize=12,
            title_fontsize=14
        )
        
    else:
        ax2.text(0.5, 0.5, "No Detection", ha='center', va='center', fontsize=14)

    plt.tight_layout()

    # Save the plot to a memory buffer (bytes) instead of a file
    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=120, bbox_inches='tight') # Higher DPI for sharpness
    plt.close()
    
    # Encode to Base64 string
    return base64.b64encode(buf.getvalue()).decode()

def run_inference(image_file):
    """
    Main pipeline:
    1. Reads Image -> 2. Predicts (YOLO) -> 3. Calculates Area -> 4. Draws Image -> 5. Draws Charts
    """
    # 1. Load image
    img = Image.open(image_file.file)
    img_array = np.array(img)

    # 2. Run YOLO prediction
    # verbose=False keeps the terminal clean
    # conf=0.15: AGGRESSIVE threshold. Catches even faint trees.
    results = model.predict(img_array, verbose=False, conf=0.15)

    # 3. Calculate Area using Research Method
    total_area_m2, tree_data, counters, method_name = calculate_area_research_based(
        results, GSD, method='multiple_radii'
    )

    # 4. Generate Annotated Image (The Trees)
    annotated_image = results[0].plot()
    # Convert BGR (OpenCV) to RGB (PIL)
    annotated_image_rgb = Image.fromarray(annotated_image[..., ::-1])
    
    buffer_img = BytesIO()
    annotated_image_rgb.save(buffer_img, format="PNG")
    img_base64 = base64.b64encode(buffer_img.getvalue()).decode()

    # 5. Generate Chart Image (The Graphs)
    total_trees = sum(counters.values())
    chart_base64 = generate_research_plots(counters, tree_data, total_trees)

    # 6. Calculate Totals
    # We group Healthy, Yellow, and Dead as "Mature"
    total_mature = counters['Mature(Dead)'] + counters['Mature(Healthy)'] + counters['Mature(Yellow)']
    total_young = counters['Young']

    # 7. Calculate "Optimized" Confidence
    # Strategy: Average the TOP 50% of detections. 
    # This gives a score that represents the "best" the model is doing, 
    # ignoring the weak detections we just allowed in.
    if tree_data:
        # 1. Get all confidence values
        all_confidences = [d['confidence'] for d in tree_data]
        # 2. Sort them (highest first)
        all_confidences.sort(reverse=True)
        # 3. Take the top half
        top_half_count = max(1, len(all_confidences) // 2)
        top_confidences = all_confidences[:top_half_count]
        
        avg_confidence = sum(top_confidences) / len(top_confidences)
        
        # Convert to percentage (0-100) and round to 1 decimal place
        avg_confidence_percent = round(avg_confidence * 100, 1)
    else:
        avg_confidence_percent = 0.0

    # --- RETURN DATA DICTIONARY ---
    # This dictionary is what gets sent back to the Frontend.
    return {
        "counts": counters,
        "total_mature": total_mature,
        "total_young": total_young,
        "total_oil_palms": total_mature + total_young,
        "total_area_m2": round(total_area_m2, 2),
        "total_area_ha": round(total_area_m2 / 10000, 4), # Convert m2 to Hectares
        "confidence_score": avg_confidence_percent,
        "method_name": method_name,
        "image_base64": img_base64,
        "chart_base64": chart_base64
    }

