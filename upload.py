import os
import re
import sys
import hashlib

from dotenv import load_dotenv
import cv2
import numpy as np
import boto3
import botocore

IMAGES_DIR = 'scans'
STORAGE_DIR = 'storage'
FULL_IMAGE_SCALE = 0.5
THUMBNAIL_W = 275
THUMBNAIL_H = 500
SCAN_FILENAME_REGEX = re.compile(r'\d{4}_[a-z]\.png')
ETAG_MD5_REGEX = re.compile(r'"?([0-9a-f]{32})"?')

POST_SCAN_BLACK_POINT = 16
POST_SCAN_WHITE_POINT = 244
POST_SCAN_SATURATION_SCALE = 1.15

FULL_RECOPY = len(sys.argv) > 1 and sys.argv[1] == '--full-recopy'


def require_env_var(name):
    value = os.getenv(name, '')
    if not value:
        raise RuntimeError('%s must be defined' % name)
    return value


def list_all_objects(s3, bucket_name):
    kwargs = {'Bucket': bucket_name}
    results = []
    while True:
        response = s3.list_objects_v2(**kwargs)
        for obj in response.get('Contents', []):
            results.append(obj)

        if not response['IsTruncated']:
            break
        kwargs['ContinuationToken'] = response['NextContinuationToken']
    return results


def get_remote_hashes(s3, bucket_name):
    hashes = {}
    for obj in list_all_objects(s3, bucket_name):
        match = ETAG_MD5_REGEX.match(obj['ETag'])
        if match:
            filename = obj['Key']
            hashes[filename] = match.group(1)
    return hashes


def get_local_hashes(dirpath):
    hashes = {}
    if os.path.isdir(dirpath):
        for filename in os.listdir(dirpath):
            with open(os.path.join(dirpath, filename), 'rb') as fp:
                h = hashlib.md5()
                while chunk := fp.read(8192):
                    h.update(chunk)
            hashes[filename] = h.hexdigest()
    return hashes


def generate_thumbnail(orig):
    if orig.shape[1] > orig.shape[0]:
        img = cv2.rotate(orig, cv2.ROTATE_90_COUNTERCLOCKWISE)
    else:
        img = orig

    h, w = img.shape[:2]
    img_aspect_ratio = w / h
    thumbnail_aspect_ratio = THUMBNAIL_W / THUMBNAIL_H

    new_h = THUMBNAIL_H
    new_w = round((THUMBNAIL_H / h) * w)
    if new_w < THUMBNAIL_W:
        new_w = THUMBNAIL_W
        new_h = round((THUMBNAIL_W / w) * h)
        assert new_h >= THUMBNAIL_H
    
    resized = cv2.resize(img, [new_w, new_h], interpolation=cv2.INTER_AREA)
    offset_x = int((new_w - THUMBNAIL_W) / 2)
    offset_y = int((new_h - THUMBNAIL_H) / 2)
    cropped = resized[offset_y:offset_y+THUMBNAIL_H, offset_x:offset_x+THUMBNAIL_W]
    return cropped


def adjust_levels(image, black_point, white_point):
    in_black = np.array([black_point, black_point, black_point], dtype=np.float32)
    in_white = np.array([white_point, white_point, white_point], dtype=np.float32)
    in_gamma = np.array([1.0, 1.0, 1.0], dtype=np.float32)
    out_black = np.array([0, 0, 0], dtype=np.float32)
    out_white = np.array([255, 255, 255], dtype=np.float32)
    image = np.clip((image - in_black) / (in_white - in_black), 0, 255)
    image = (image ** (1 / in_gamma)) * (out_white - out_black) + out_black
    return np.clip(image, 0, 255).astype(np.uint8)


def saturate(image, saturation_scale):
    hsv = cv2.cvtColor(image.astype(np.float32), cv2.COLOR_BGR2HSV)
    hsv *= (1.0, saturation_scale, 1.0)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR).astype(np.uint8)


def copy_to_storage():
    if not os.path.isdir(STORAGE_DIR):
        os.makedirs(STORAGE_DIR)

    scan_basenames = {os.path.splitext(f)[0] for f in os.listdir(IMAGES_DIR) if SCAN_FILENAME_REGEX.match(f)}
    storage_basenames = {os.path.splitext(f)[0] for f in os.listdir(STORAGE_DIR)}
    basenames_to_copy = scan_basenames if FULL_RECOPY else (scan_basenames - storage_basenames)

    for basename in sorted(basenames_to_copy):
        scan_filepath = os.path.join(IMAGES_DIR, basename + '.png')
        storage_filepath = os.path.join(STORAGE_DIR, basename + '.jpg')

        print('Compressing image %s and copying to storage...' % basename)
        image = cv2.imread(scan_filepath)
        image = saturate(adjust_levels(image, POST_SCAN_BLACK_POINT, POST_SCAN_WHITE_POINT), POST_SCAN_SATURATION_SCALE)
        image = cv2.resize(image, [image.shape[1] * FULL_IMAGE_SCALE, image.show[0] * FULL_IMAGE_SCALE], interpolation=cv2.INTER_AREA)
        cv2.imwrite(storage_filepath, image, [int(cv2.IMWRITE_JPEG_QUALITY), 70])

        if basename.endswith('_a'):
            print('Generating thumbnail for image %s...' % basename)
            thumbnail_filepath = os.path.join(STORAGE_DIR, basename.replace('_a', '') + '_thumb.jpg')
            thumbnail = generate_thumbnail(image)
            cv2.imwrite(thumbnail_filepath, thumbnail, [int(cv2.IMWRITE_JPEG_QUALITY), 70])


def sync_to_remote(s3, bucket_name):
    remote_hashes = get_remote_hashes(s3, bucket_name)
    local_hashes = get_local_hashes(STORAGE_DIR)

    num_files_uploaded = 0

    for filename, local_hash in sorted(local_hashes.items()):
        needs_upload = False
        remote_hash = remote_hashes.get(filename, '')
        if not remote_hash:
            print('+ %s is new.' % filename)
            needs_upload = True
        elif remote_hash != local_hash:
            print('+ %s has been modified.' % filename)
            needs_upload = True
        else:
            print('| %s is unchanged.' % filename)

        if needs_upload:
            data = b''
            with open(os.path.join(STORAGE_DIR, filename), 'rb') as fp:
                data = fp.read()

            sys.stdout.write('Uploading %s (%d bytes)... ' % (filename, len(data)))
            try:
                s3.put_object(Bucket=bucket_name, Key=filename, Body=data, ACL='public-read')
            except:
                print('')
                raise
    
            num_files_uploaded += 1
            print('OK.')

    print('Uploaded %d files.' % num_files_uploaded)


if __name__ == '__main__':
    load_dotenv()
    bucket_name = require_env_var('SPACES_BUCKET_NAME')
    region_name = require_env_var('SPACES_REGION_NAME')
    endpoint_url = 'https://' + require_env_var('SPACES_ENDPOINT_URL')
    aws_access_key_id = require_env_var('SPACES_ACCESS_KEY_ID')
    aws_secret_access_key = require_env_var('SPACES_SECRET_KEY')

    session = boto3.session.Session()
    config = botocore.config.Config(s3={'addressing_style': 'virtual'})
    s3 = session.client('s3', config=config, region_name=region_name, endpoint_url=endpoint_url, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)

    copy_to_storage()
    sync_to_remote(s3, bucket_name)
