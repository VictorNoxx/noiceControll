from PIL import Image, ImageDraw

# Create a new image with a white background
size = (256, 256)
img = Image.new('RGB', size, '#0078d4')
draw = ImageDraw.Draw(img)

# Draw a simple sound wave icon
padding = 40
wave_height = size[1] - 2 * padding
wave_width = size[0] - 2 * padding

# Draw vertical lines
x_positions = [padding + wave_width * x / 4 for x in range(5)]
heights = [0.5, 0.8, 1.0, 0.8, 0.5]  # Relative heights

for x, height in zip(x_positions, heights):
    line_height = wave_height * height
    y1 = (size[1] - line_height) / 2
    y2 = y1 + line_height
    draw.line([(x, y1), (x, y2)], fill='white', width=16)

# Save as ICO
img.save('app_icon.ico', format='ICO') 