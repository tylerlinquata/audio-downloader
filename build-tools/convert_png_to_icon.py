#!/usr/bin/env python3
"""
Script to convert a PNG file to macOS ICNS format for the Danish Audio Downloader app.
"""

from PIL import Image, ImageDraw
import os
import sys

def create_rounded_mask(size, radius_ratio=0.225):
    """Create a rounded rectangle mask for macOS-style icons."""
    # Calculate radius based on Apple's design guidelines
    # Apple uses approximately 22.5% of the icon size as radius
    radius = int(size * radius_ratio)
    
    # Create a mask
    mask = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(mask)
    
    # Draw rounded rectangle
    draw.rounded_rectangle(
        [(0, 0), (size-1, size-1)],
        radius=radius,
        fill=255
    )
    
    return mask

def apply_rounded_corners(img, size):
    """Apply rounded corners to an image."""
    # Create rounded mask
    mask = create_rounded_mask(size)
    
    # Ensure image is RGBA
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Resize image to exact size
    img = img.resize((size, size), Image.LANCZOS)
    
    # Apply mask
    img.putalpha(mask)
    
    return img

def convert_png_to_icns(png_path, output_name="app_icon"):
    """Convert a PNG file to ICNS format with all required sizes and rounded corners."""
    
    if not os.path.exists(png_path):
        print(f"Error: PNG file '{png_path}' not found.")
        return False
    
    try:
        # Open the PNG image
        print(f"Opening PNG file: {png_path}")
        img = Image.open(png_path)
        
        # Convert to RGBA if not already
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Create iconset directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        iconset_dir = os.path.join(script_dir, f"{output_name}.iconset")
        
        if os.path.exists(iconset_dir):
            import shutil
            shutil.rmtree(iconset_dir)
        os.makedirs(iconset_dir)
        
        print(f"Creating iconset in: {iconset_dir}")
        
        # Create different sizes required for macOS iconset
        icon_sizes = [16, 32, 64, 128, 256, 512, 1024]
        
        for size in icon_sizes:
            print(f"Creating {size}x{size} icon with rounded corners...")
            
            # Regular size with rounded corners
            rounded_img = apply_rounded_corners(img, size)
            rounded_img.save(f"{iconset_dir}/icon_{size}x{size}.png")
            
            # @2x size (high DPI) - only for sizes that won't exceed 1024
            if size <= 512:
                double_size = size * 2
                rounded_img_2x = apply_rounded_corners(img, double_size)
                rounded_img_2x.save(f"{iconset_dir}/icon_{size}x{size}@2x.png")
        
        print(f"Iconset created successfully in: {iconset_dir}")
        
        # Now convert to ICNS using iconutil
        icns_path = os.path.join(script_dir, f"{output_name}.icns")
        print(f"Converting to ICNS format: {icns_path}")
        
        import subprocess
        result = subprocess.run([
            'iconutil', '-c', 'icns', iconset_dir, '-o', icns_path
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Successfully created ICNS file: {icns_path}")
            return True
        else:
            print(f"❌ Error creating ICNS file: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Error processing PNG file: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python convert_png_to_icon.py <path_to_png_file>")
        print("Example: python convert_png_to_icon.py my_icon.png")
        sys.exit(1)
    
    png_path = sys.argv[1]
    success = convert_png_to_icns(png_path)
    
    if success:
        print("\n🎉 Icon conversion completed successfully!")
        print("Your new app_icon.icns file is ready to use.")
    else:
        print("\n❌ Icon conversion failed.")
        sys.exit(1)
