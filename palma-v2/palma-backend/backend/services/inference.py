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
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # --- CHART 1: CANOPY SIZE HISTOGRAM ---
    # Extract areas of all trees
    areas = [t['area_m2'] for t in tree_data]
    
    if areas:
        # Create a histogram of tree sizes
        # Color: Dark Green for vegetation
        ax1.hist(areas, bins=15, color='#2e7d32', alpha=0.7, edgecolor='black')
        ax1.set_title('Tree Crown Size Distribution', fontsize=12, fontweight='bold')
        ax1.set_xlabel('Canopy Area (m²)')
        ax1.set_ylabel('Frequency (Trees)')
        ax1.grid(axis='y', alpha=0.3)
        
        # Add a vertical line for the average size
        avg_area = np.mean(areas)
        ax1.axvline(avg_area, color='red', linestyle='dashed', linewidth=1)
        ax1.text(avg_area*1.05, ax1.get_ylim()[1]*0.9, f'Avg: {avg_area:.1f} m²', color='red', fontsize=9)
    else:
        ax1.text(0.5, 0.5, "No Area Data", ha='center', va='center')
    
    # --- CHART 2: COMPOSITION DONUT CHART ---
    # Filter out zero counts so we don't have empty labels
    labels = [k for k, v in counters.items() if v > 0]
    sizes = [v for k, v in counters.items() if v > 0]
    
    # Define custom colors map for consistent reporting
    colors_map = {
        'Mature(Healthy)': '#2e7d32', # Dark Green
        'Mature(Yellow)': '#f9a825',  # Yellow/Orange
        'Mature(Dead)': '#c62828',    # Red
        'Young': '#7cb342',           # Light Green
        'Grass': '#8d6e63'            # Brown
    }
    # Create list of colors matching the active labels
    plot_colors = [colors_map.get(label, 'gray') for label in labels]

    if sizes:
        wedges, texts, autotexts = ax2.pie(
            sizes, 
            labels=labels, 
            autopct='%1.1f%%', 
            startangle=90, 
            colors=plot_colors, 
            pctdistance=0.85,
            wedgeprops=dict(width=0.3, edgecolor='white') # width=0.3 creates the "Donut" hole
        )
        
        # Style the text labels
        plt.setp(texts, size=9, weight="bold")
        plt.setp(autotexts, size=8, weight="bold", color="white")
        
        ax2.set_title('Plantation Composition', fontsize=12, fontweight='bold')
        
        # Add total count in the middle of the donut hole
        ax2.text(0, 0, f"{total_trees}\nTrees", ha='center', va='center', fontsize=14, fontweight='bold', color='#333')
    else:
        ax2.text(0.5, 0.5, "No Detection", ha='center', va='center')

    plt.tight_layout()

    # Save the plot to a memory buffer (bytes) instead of a file
    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=100)
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
    results = model.predict(img_array, verbose=False)

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

    # --- RETURN DATA DICTIONARY ---
    # This dictionary is what gets sent back to the Frontend.
    return {
        "counts": counters,
        "total_mature": total_mature,
        "total_young": total_young,
        "total_oil_palms": total_mature + total_young,
        "total_area_m2": round(total_area_m2, 2),
        "total_area_ha": round(total_area_m2 / 10000, 4), # Convert m2 to Hectares
        "method_name": method_name,
        "image_base64": img_base64,
        "chart_base64": chart_base64
    }