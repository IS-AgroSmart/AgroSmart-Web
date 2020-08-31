from PIL import Image, ImageDraw, ImageFont
from matplotlib import colors


def pseudocolor(val, minval, maxval):
    data = {'red': [(0.0, 1.0, 1.0),
                    (0.1, 0.5, 0.5),
                    (0.2, 0.0, 0.0),
                    (0.3, 0.0, 0.0),
                    (0.4, 0.0, 0.0),
                    (0.5, 0.0, 0.0),
                    (0.6, 0.0, 0.0),
                    (0.7, 0.5, 0.5),
                    (0.8, 1.0, 1.0),
                    (0.9, 1.0, 1.0),
                    (1.0, 1.0, 1.0)],

            'green': [(0.0, 0.0, 0.0),
                      (0.1, 0.0, 0.0),
                      (0.2, 0.0, 0.0),
                      (0.3, 0.5, 0.5),
                      (0.4, 1.0, 1.0),
                      (0.5, 1.0, 1.0),
                      (0.6, 1.0, 1.0),
                      (0.7, 1.0, 1.0),
                      (0.8, 1.0, 1.0),
                      (0.9, 0.5, 0.5),
                      (1.0, 0.0, 0.0)],

            'blue': [(0.0, 1.0, 1.0),
                     (0.1, 1.0, 1.0),
                     (0.2, 1.0, 1.0),
                     (0.3, 1.0, 1.0),
                     (0.4, 1.0, 1.0),
                     (0.5, 0.5, 0.5),
                     (0.6, 0.0, 0.0),
                     (0.7, 0.0, 0.0),
                     (0.8, 0.0, 0.0),
                     (0.9, 0.0, 0.0),
                     (1.0, 0.0, 0.0)]}
    cmap = colors.LinearSegmentedColormap("mycustommap", data)

    val = (val - minval) / (maxval - minval)
    color = cmap(val)
    return tuple(int(x * 255) for x in color)


def center_text(img, font, text, strip, color=(0, 0, 0)):
    draw = ImageDraw.Draw(img)
    text_width, text_height = draw.textsize(text, font)
    strip_width, strip_height = strip
    position = ((strip_width - text_width) / 2, (strip_height - text_height) / 2)
    draw.text(position, text, color, font=font)
    return img


def left_text(img, font, text, strip, color=(0, 0, 0)):
    draw = ImageDraw.Draw(img)
    strip_x, strip_y = strip
    position = (strip_x, strip_y)
    draw.text(position, text, color, font=font)
    return img


def right_text(img, font, text, strip, color=(0, 0, 0)):
    draw = ImageDraw.Draw(img)
    w, h = draw.textsize(text, font)
    strip_x, strip_y = strip
    position = (strip_x - w, strip_y)
    draw.text(position, text, color, font=font)
    return img


N = 500
HEIGHT = 20


def create_colorbar(min_label, max_label, save_path):
    gradient = Image.new('RGBA', (N, 1))
    for i in range(N):
        rgb_val = pseudocolor(i, 0, N)
        gradient.putpixel((i, 0), rgb_val)

    base = Image.new("RGBA", (N, 80))
    gradient = gradient.resize((N, HEIGHT))
    font = ImageFont.truetype("DejaVuSans.ttf", 20)

    base.paste(gradient, (0, 0))
    left_text(base, font, min_label, (0, HEIGHT + 5))
    right_text(base, font, max_label, (N - 1, HEIGHT + 5))

    base.save(save_path, "PNG")
