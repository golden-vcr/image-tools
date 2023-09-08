import os
import sys
import re
import struct

import numpy as np
import cv2

IMAGES_DIR = 'scans'


def read_png_dimensions(filepath):
    with open(filepath, 'rb') as fp:
        signature = fp.read(8)
        if signature != b'\x89PNG\r\n\x1a\n':
            raise RuntimeError('not a .png: signature mismatch')
        (ihdr_length,) = struct.unpack('>I', fp.read(4))
        if ihdr_length < 8:
            raise RuntimeError('unexpected IHDR length: %d', ihdr_length)
        chunk_type = fp.read(4)
        if chunk_type != b'IHDR':
            raise RuntimeError('unexpected type for first chunk: %s' % chunk_type)
        w, h = struct.unpack('>II', fp.read(8))
        return w, h


def get_scale_factor_to_fit(im, max_w, max_h):
    h, w = im.shape[:2]
    if w <= max_w and h <= max_h:
        return im

    aspect_ratio = w / h
    new_w, new_h = round(max_h * aspect_ratio), max_h
    if new_w > max_w:
        new_w, new_h = max_w, round(max_w / aspect_ratio)
    return new_w / w


def last_nonzero(im, axis):
    bools = im != 0
    val = im.shape[axis] - np.flip(bools, axis=axis).argmax(axis=axis) - 1
    return np.where(bools.any(axis=axis), val, -1)


def reject_outliers(data, m = 2.0):
    d = np.abs(data - np.median(data))
    mdev = np.median(d)
    s = d / mdev if mdev else np.zeros(len(d))
    return data[s < m]


def find_crop_edge(im, axis):
    coords = last_nonzero(im, axis)
    series = np.sort(coords[coords >= 0])
    return np.max(reject_outliers(series))


def find_crop_dimensions(plate, orig):
    h, w = orig.shape[:2]

    diff = cv2.absdiff(orig, plate)
    blurred = cv2.GaussianBlur(diff, (3, 3), 0)
    gray = cv2.cvtColor(blurred, cv2.COLOR_RGB2GRAY)
    _, thresholded = cv2.threshold(gray, 16, 255, cv2.THRESH_BINARY)

    new_h = find_crop_edge(thresholded, 0)
    new_w = find_crop_edge(thresholded, 1)
    return [new_h, new_w]


def apply_crop_overlay(orig, new_h, new_w):
    h, w = orig.shape[:2]
    mask_row = (np.arange(w, dtype=int) < new_w)
    mask_col = (np.arange(h, dtype=int) < new_h)
    mask_x = np.tile(mask_row, (h, 1))
    mask_y = np.transpose(np.tile(mask_col, (w, 1)))
    mask = np.bitwise_and(mask_x, mask_y)
    mask_rgb = cv2.cvtColor(mask * np.uint8(255), cv2.COLOR_GRAY2RGB)
    overlay = cv2.multiply((255 - mask_rgb), (0, 0.2, 0, 0))
    return orig + overlay


def interactive_crop(filepath, plate, orig):
    filename = os.path.basename(filepath)
    h, w = orig.shape[:2]
    scale_factor = get_scale_factor_to_fit(orig, 1920, 1080)

    auto_h, auto_w = find_crop_dimensions(plate, orig)
    new_h, new_w = auto_h, auto_w

    overlaid = apply_crop_overlay(orig, new_h, new_w)
    resized = cv2.resize(overlaid, [round(w * scale_factor), round(h *scale_factor)])
    last_rendered_crop_dim = (new_h, new_w)

    def handle_mouse_event(event, x, y, flags, param):
        nonlocal new_h, new_w
        if event == 1 and flags == 1:
            new_h = round(y / scale_factor)
            new_w = round(x / scale_factor)

    cv2.imshow(filename, resized)
    cv2.moveWindow(filename, 0, 0)
    cv2.setMouseCallback(filename, handle_mouse_event)

    KEY_ESC = 27
    KEY_Q = 113
    KEY_R = 114
    KEY_ARROW_UP = 2490368
    KEY_ARROW_DOWN = 2621440
    KEY_ARROW_LEFT = 2424832
    KEY_ARROW_RIGHT = 2555904

    while True:
        key = cv2.waitKeyEx(33)
        if key in (KEY_ESC, KEY_Q):
            sys.exit(1)
        elif key == KEY_R:
            new_h = auto_h
            new_w = auto_w
        elif key in (KEY_ARROW_UP, KEY_ARROW_DOWN, KEY_ARROW_LEFT, KEY_ARROW_RIGHT):
            cv2.destroyAllWindows()
            cropped = orig[0:new_h, 0:new_w]
            if key == KEY_ARROW_DOWN:
                return cv2.rotate(cropped, cv2.ROTATE_180)
            elif key == KEY_ARROW_LEFT:
                return cv2.rotate(cropped, cv2.ROTATE_90_CLOCKWISE)
            elif key == KEY_ARROW_RIGHT:
                return cv2.rotate(cropped, cv2.ROTATE_90_COUNTERCLOCKWISE)
            return cropped
        elif key == -1 and (new_h, new_w) != last_rendered_crop_dim:
            overlaid = apply_crop_overlay(orig, new_h, new_w)
            resized = cv2.resize(overlaid, [round(w * scale_factor), round(h *scale_factor)])
            cv2.imshow(filename, resized)
            last_rendered_crop_dim = (new_h, new_w)


if __name__ == '__main__':
    # Load a clean background-plate scan so we can diff against each scanned image
    plate_path = os.path.join(IMAGES_DIR, '_plate.png')
    if not os.path.isfile(plate_path):
        print('ERROR: _plate.png not found at: %s' % plate_path)
        print('Please scan a clean background plate and try again.')
        sys.exit(1)
    plate = cv2.imread(plate_path)

    # Iterate over all files in the images directory
    for filename in sorted(os.listdir(IMAGES_DIR)):

        # If the file isn't a scan .png, skip it
        match = re.match(r'\d{4}_([a-z])\.png', filename)
        if not match:
            continue
        filepath = os.path.join(IMAGES_DIR, filename)

        # Determine if the image has already been cropped, in which case we can skip loading it for now
        existing_w, existing_h = read_png_dimensions(filepath)
        needs_crop = existing_w == plate.shape[1] and existing_h == plate.shape[0]
        if needs_crop:
            # Prompt the user to crop the image, then overwrite it
            orig = cv2.imread(filepath)
            cropped = interactive_crop(filepath, plate, orig)
            cv2.imwrite(filepath, cropped)
            print('%s overwritten.' % filename)
        else:
            # Skip cropping if the image size is no longer the original scan size
            print('%s already cropped.' % filename)
