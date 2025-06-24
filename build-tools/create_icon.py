#!/usr/bin/env python3
# Script to create an app icon for the Danish Word Audio Downloader

from PIL import Image, ImageDraw, ImageFont
import os
import sys
import math

def create_icon():
    print("Starting icon creation...")
    # Create a 1024x1024 image with gradient background
    icon_size = 1024
    img = Image.new('RGB', (icon_size, icon_size), color=(240, 245, 255))  # Light blue-gray
    draw = ImageDraw.Draw(img)
    
    # Danish flag colors
    danish_red = (198, 12, 48)    # Official Danish red
    danish_white = (255, 255, 255)
    danish_blue = (0, 61, 165)    # Dark blue accent
    audio_green = (76, 175, 80)   # Green for audio/download theme
    
    center_x, center_y = icon_size // 2, icon_size // 2
    
    print("Drawing main circle background...")
    # Draw main circle with gradient-like effect
    main_radius = icon_size // 2.2
    # Outer shadow circle
    shadow_offset = 8
    draw.ellipse(
        (center_x - main_radius + shadow_offset, center_y - main_radius + shadow_offset,
         center_x + main_radius + shadow_offset, center_y + main_radius + shadow_offset), 
        fill=(200, 200, 200, 100)
    )
    # Main white circle
    draw.ellipse(
        (center_x - main_radius, center_y - main_radius,
         center_x + main_radius, center_y + main_radius), 
        fill=danish_white, outline=(220, 220, 220), width=4
    )
    
    print("Drawing Danish flag element...")
    # Draw a subtle Danish flag cross in the background
    flag_size = main_radius * 1.2
    cross_width = 30
    # Horizontal bar
    draw.rectangle(
        (center_x - flag_size//2, center_y - cross_width//2,
         center_x + flag_size//2, center_y + cross_width//2),
        fill=(danish_red[0], danish_red[1], danish_red[2], 40)  # Semi-transparent
    )
    # Vertical bar (slightly off-center like real Danish flag)
    vertical_offset = -flag_size//8
    draw.rectangle(
        (center_x + vertical_offset - cross_width//2, center_y - flag_size//2,
         center_x + vertical_offset + cross_width//2, center_y + flag_size//2),
        fill=(danish_red[0], danish_red[1], danish_red[2], 40)  # Semi-transparent
    )
    
    print("Drawing audio speaker...")
    # Draw a modern speaker/audio icon in the center-left
    speaker_x = center_x - 120
    speaker_y = center_y - 60
    speaker_width = 40
    speaker_height = 120
    
    # Speaker body (rectangular)
    draw.rectangle(
        (speaker_x, speaker_y, speaker_x + speaker_width, speaker_y + speaker_height),
        fill=danish_blue, outline=danish_red, width=3
    )
    
    # Speaker cone (triangle extending right)
    cone_points = [
        (speaker_x + speaker_width, speaker_y + 20),
        (speaker_x + speaker_width + 60, speaker_y + 40),
        (speaker_x + speaker_width + 60, speaker_y + 80),
        (speaker_x + speaker_width, speaker_y + 100)
    ]
    draw.polygon(cone_points, fill=danish_blue, outline=danish_red, width=3)
    
    print("Drawing sound waves...")
    # Draw elegant sound wave arcs
    wave_start_x = speaker_x + speaker_width + 80
    wave_colors = [(audio_green[0], audio_green[1], audio_green[2], 200),
                   (audio_green[0], audio_green[1], audio_green[2], 150),
                   (audio_green[0], audio_green[1], audio_green[2], 100)]
    
    for i, color in enumerate(wave_colors):
        radius = 80 + i * 40
        wave_width = 12 - i * 2
        # Create multiple short arcs to simulate sound waves
        for angle_offset in range(-30, 31, 15):
            start_angle = 315 + angle_offset
            end_angle = start_angle + 30
            draw.arc(
                (wave_start_x - radius, center_y - radius,
                 wave_start_x + radius, center_y + radius),
                start_angle, end_angle, fill=color[:3], width=wave_width
            )
    
    print("Drawing download arrow...")
    # Draw a download arrow in the bottom right
    arrow_x = center_x + 80
    arrow_y = center_y + 80
    arrow_size = 60
    
    # Arrow shaft
    draw.rectangle(
        (arrow_x - 15, arrow_y - arrow_size//2,
         arrow_x + 15, arrow_y + arrow_size//2),
        fill=audio_green
    )
    
    # Arrow head
    arrow_head = [
        (arrow_x - 40, arrow_y + arrow_size//2 - 20),
        (arrow_x, arrow_y + arrow_size//2 + 20),
        (arrow_x + 40, arrow_y + arrow_size//2 - 20)
    ]
    draw.polygon(arrow_head, fill=audio_green)
    
    print("Adding Danish text...")
    # Add "DA" text in top area with Danish flag colors
    text_y = center_y - 180
    letter_size = 80
    letter_width = 15
    
    # Draw "D"
    d_x = center_x - 60
    # Vertical line
    draw.rectangle((d_x, text_y, d_x + letter_width, text_y + letter_size), fill=danish_red)
    # Horizontal lines for D
    draw.rectangle((d_x, text_y, d_x + 50, text_y + letter_width), fill=danish_red)
    draw.rectangle((d_x, text_y + letter_size - letter_width, d_x + 50, text_y + letter_size), fill=danish_red)
    # Curved part of D (approximated with rectangles)
    for i in range(5):
        offset = i * 8
        width = 50 - offset
        draw.rectangle((d_x + width, text_y + offset + 10, d_x + width + 8, text_y + offset + 18), fill=danish_red)
        draw.rectangle((d_x + width, text_y + letter_size - offset - 18, d_x + width + 8, text_y + letter_size - offset - 10), fill=danish_red)
    
    # Draw "A"
    a_x = center_x + 10
    # Left diagonal
    points_left = [(a_x, text_y + letter_size), (a_x + 10, text_y + letter_size), (a_x + 30, text_y), (a_x + 20, text_y)]
    draw.polygon(points_left, fill=danish_red)
    # Right diagonal  
    points_right = [(a_x + 30, text_y), (a_x + 40, text_y), (a_x + 60, text_y + letter_size), (a_x + 50, text_y + letter_size)]
    draw.polygon(points_right, fill=danish_red)
    # Horizontal bar
    draw.rectangle((a_x + 20, text_y + letter_size//2 - 5, a_x + 40, text_y + letter_size//2 + 5), fill=danish_red)
    
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
