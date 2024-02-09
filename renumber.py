import os
import re
import sys

REGEX_SCAN = re.compile(r'scan_\d{4}\.png')
REGEX_IMAGE = re.compile(r'(\d{4})_[a-z]\.png')
DRY_RUN = len(sys.argv) > 1 and sys.argv[1] in ('-n', '--dry-run')

images_root = os.path.abspath(os.path.join(os.path.dirname(__file__), 'scans'))

max_existing_tape_id = 0
scan_filenames = set()

filenames = os.listdir(images_root)
for filename in filenames:
    scan_match = REGEX_SCAN.match(filename)
    if scan_match:
        scan_filenames.add(filename)
        continue
    
    image_match = REGEX_IMAGE.match(filename)
    if image_match:
        tape_id = int(image_match.group(1))
        if tape_id > max_existing_tape_id:
            max_existing_tape_id = tape_id
        continue

if not scan_filenames:
    print('No files to rename.')
    sys.exit(0)

new_tape_id = max_existing_tape_id + 1
for i, src_filename in enumerate(sorted(scan_filenames)):
    dst_filename = '%04d_%s.png' % (new_tape_id, chr(ord('a') + i))
    if DRY_RUN:
        print('Would rename: %s -> %s' % (src_filename, dst_filename))
    else:
        src_filepath = os.path.join(images_root, src_filename)
        dst_filepath = os.path.join(images_root, dst_filename)
        os.rename(src_filepath, dst_filepath)
        print('Renamed: %s -> %s' % (src_filename, dst_filename))

if DRY_RUN:
    print('Dry-run completed. No files were renamed.')
else:
    print('Files renamed successfully.')
