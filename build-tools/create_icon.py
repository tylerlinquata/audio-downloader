#!/usr/bin/env python3
# Script to create an app icon for the Danish Word Audio Downloader

from PIL import Image, ImageDraw, ImageFont
import os
import sys

def create_icon():
    print("Starting icon creation...")
    # Create a 1024x1024 image with a blue background
    icon_size = 1024
    img = Image.new('RGB', (icon_size, icon_size), color=(65, 105, 225))  # Royal Blue
    draw = ImageDraw.Draw(img)
    
    print("Drawing circle...")
    # Draw a white circle in the center
    circle_center = (icon_size // 2, icon_size // 2)
    circle_radius = icon_size // 2.5
    draw.ellipse(
        (circle_center[0] - circle_radius, 
         circle_center[1] - circle_radius,
         circle_center[0] + circle_radius, 
         circle_center[1] + circle_radius), 
        fill=(255, 255, 255)
    )
    
    print("Drawing sound waves...")
    # Draw a sound wave symbol
    wave_color = (65, 105, 225)  # Royal Blue
    wave_width = 20
    center_x, center_y = circle_center
    
    # Draw three sound wave arcs
    for i in range(3):
        radius = 150 + i * 60
        draw.arc(
            (center_x - radius, center_y - radius, center_x + radius, center_y + radius),
            45, 135, fill=wave_color, width=wave_width
        )
    
    print("Adding text...")
    # Add text "DK" at the bottom - simplified to avoid font issues
    text = "DK"
    text_color = (65, 105, 225)  # Royal Blue
    
    # Draw text manually since font loading might be problematic
    # Draw a large "D"
    d_start_x = center_x - 100
    d_start_y = center_y + 50
    d_width = 80
    d_height = 150
    
    # D vertical line
    draw.rectangle((d_start_x, d_start_y, d_start_x + 20, d_start_y + d_height), fill=text_color)
    # D curve
    draw.arc((d_start_x, d_start_y, d_start_x + d_width, d_start_y + d_height), 270, 90, fill=text_color, width=20)
    
    # Draw a large "K"
    k_start_x = center_x + 20
    k_start_y = d_start_y
    k_height = d_height
    
    # K vertical line
    draw.rectangle((k_start_x, k_start_y, k_start_x + 20, k_start_y + k_height), fill=text_color)
    # K diagonals
    draw.line((k_start_x, k_start_y + k_height/2, k_start_x + 80, k_start_y), fill=text_color, width=20)
    draw.line((k_start_x, k_start_y + k_height/2, k_start_x + 80, k_start_y + k_height), fill=text_color, width=20)
    
    print("Saving main icon...")
    # Save the PNG version
    png_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.png")
    img.save(png_path)
    print(f"Created {png_path}")
    
    print("Creating iconset...")
    # Save in various sizes for the iconset
    iconset_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.iconset")
    if not os.path.exists(iconset_dir):
        os.makedirs(iconset_dir)
    
    # Create different sizes required for macOS iconset
    icon_sizes = [16, 32, 64, 128, 256, 512, 1024]
    for size in icon_sizes:
        print(f"Creating {size}x{size} icon...")
        # Regular size
        resized_img = img.resize((size, size), Image.LANCZOS)
        resized_img.save(f"{iconset_dir}/icon_{size}x{size}.png")
        
        # @2x size (high DPI)
        if size * 2 <= 1024:
            double_size = size * 2
            resized_img = img.resize((double_size, double_size), Image.LANCZOS)
            resized_img.save(f"{iconset_dir}/icon_{size}x{size}@2x.png")
    
    print(f"Created iconset in {iconset_dir}")
    return png_path, iconset_dir

if __name__ == "__main__":
    try:
        png_path, iconset_dir = create_icon()
        print(f"Icon creation completed successfully.")
        print(f"PNG path: {png_path}")
        print(f"Iconset directory: {iconset_dir}")
        print("Now run: iconutil -c icns app.iconset -o app_icon.icns")
    except Exception as e:
        print(f"Error creating icon: {e}", file=sys.stderr)
        sys.exit(1)
