# image-tools

The **image-tools** repo contains tools and scripts that aid in the process of scanning
and cataloguing new tapes as they're added to the Golden VCR library. This is a largely
manual workflow that takes place locally.

## Prerequisites

1. Get some little [self-adhesive labels](https://www.target.com/p/128ct-1-34-x2-75-34-rectangular-labels-white-up-38-up-8482/-/A-14471285)
   that you can write on with a pen and stick onto tapes.
2. Connect a scanner to your computer: I'm using a Canon CanoScan 9000F Mark II.
3. Establish a work directory to contain your scanned images: by default, this is
   `image-tools/scans`.
4. Install [NAPS2](https://www.naps2.com/).
5. Open NAPS2 and create a profile to scan at 300 dpi, letter size, with auto-save
   configured to write images to your work directory with the filename pattern
   `scan_$(nnnn).png`. Note the hotkey associated with this new profile (e.g. `F2`).
6. Install the latest version of [Python 3](https://www.python.org/downloads/).
7. Install dependencies with `pip install -r requirements.txt`.
8. Prepare an `.env` file defining the environment variables required by
   [`upload.py`](./upload.py). If you have the [`terraform`](https://github.com/golden-vcr/terraform)
   repo cloned alongside this one, simply open a shell there and run
   `terraform output -raw images_s3_env > ../image-tools/.env`.

## Workflow

### Assigning IDs and logging tapes

The first step in adding new tapes to the collection is to assign each tape a
sequential ID and enter its basic details into a spreadsheet.

When you're ready to get started:

- Open the [Golden VCR Inventory](https://docs.google.com/spreadsheets/d/1cR9Lbw9_VGQcEn8eGD2b5MwGRGzKugKZ9PVFkrqmA7k/edit)
  spreadsheet.
- Prepare a set of labels, starting from the next available tape ID. e.g. if the last
  tape entered into the spreadsheet had ID 52, write and cut out labels for 53, 54, 55,
  and so on, small enough that they can be stuck onto the edge of the VHS cassette.

Now grab a handful of tapes. For each tape:

1. Examine the reels for mold or other damage. If the tape is moldy, discard it.
2. Enter the title of the tape in the next available row, and ensure that the ID column
   is populated with the next integer in the sequence.
3. Grab the label for that ID and stick it onto the edge of the cassette.
4. Check for any information about publication year or runtime: if available, enter the
   year and/or runtime (in minutes) into the spreadsheet.

Repeat as desired until you're ready to scan a batch of tapes.

### Scanning and renaming tape images

Once you've got a handful of tapes catalogued, it's time to capture some images of the
tape. Images are correlated to entries in the spreadsheet based on ID: e.g. if we want
the images scanned from tape 53, we'll simply look for `0053_a.png`, `0053_b.png`, and
so on.

Most tapes have three images: an `a` image for the front of the case, a `b` image for
the back of the case, and a `c` image for the labeled side of the cassette. A tape with
no case may simply have an `a` image showing the cassette. Scans of other relevant
sides, included printed materials, etc., may be saved as `d`, `e`, and so on.

The [`renumber.py`](./renumber.py) script allows us to quickly rename tape images en
masse as we scan them. To get started scanning:

- Turn on your scanner, open the lid, and clean the glass if necessary.
- Open NAPS2.
- Open a file explorer window in the `scans` directory.
- Open a shell in the root of this repo.

Each image should be scanned with the tape pressed flush against both sides of the
scanner as indicated by the registration mark. You can initiate a scan from NAPS2 by
simply pressing the hotkey associated with the profile you created earlier.

For each tape, proceeding in sequence based on ID number:

1. If the tape has a case, place it face-down on the scanner and initiate a scan. Then
   flip the case over and initiate a scan of the back.
2. Place the cassette itself face-down on the scanner and initiate a scan.
3. If the tape contains supplemental printed materials, or if the edges of the tape or
   case contain relevant information that should be captured, create more scans as
   needed.
4. In your shell, run `python3 renumber.py`.
     - This should automatically rename the new images in your `scans` directory, e.g.
       from `scan_0001.png`, `scan_0002.png`, etc. to `0053_a.png`, `0053_b.png`, etc.
     - The tape ID assigned to the images will be the next ID in the sequence, based on
       the existin gimages in the `scans` directory.

Once you've scanned all the tapes that you previously catalogued, you can grab another
batch of tapes and add them to the spreadsheet. When you've finished scanning and are
ready to move on, then it's time to process your scanned images and get them ready for
upload.

### Scanning a clean background plate

Once you've finished scanning and you're about to move on to cropping, you'll want to
scan one more image:

1. Clear the bed of the scanner, and clean the glass if necessary.
2. Leave the lid opened to the same approximate angle it's been opened to while
   scanning tapes.
3. Initiate a scan.
4. Rename the resulting image to `_plate.png`.

This image is required by the automatic cropping script.

### Cropping/rotating tape images and generating thumbnails

Once your `scans` directory has been populated with new scanned-and-renamed images, you
can use the [`crop.py`](./crop.py) script to run through them and quickly crop each
image. To get started:

- Run `python3 crop.py`

The script will automatically iterate through scanned images, allowing you to crop each
one, and suggesting a default crop based on where it thinks the edges of the tape lie
in the image. If an image has already been cropped, the script will skip it: it's safe
to re-run the script as many times as you like for the same set of images.

For each image that needs to be cropped, a window will appear showing the tape image,
with a green mask indicating where the image will be cropped. From here, you may:

- Click on the image to adjust where the crop will occur.
- Press **R** to reset the crop to the original, automatic result.
- Press the **Up"**, **Down**, **Left**, or **Right** arrow keys to accept the crop,
  rotating the image as needed so that the indicated direction becomes up.
- Press **Q** or **Esc** to exit the program and perform no further cropping.

When accepting the crop, imagine that you're pointing toward the top of the text in the
image:

- If the image is already in the correct orientation: press **Up**.
- If the top of the text is at the bottom of the frame, such that the image needs to be
  rotated 180 degrees, press **Down**.
- If the top of the text is at the left of the frame, press **Left**.
- If the top of the text is at the right of the frame, press **Right**.

When finished, review your images in the `scans` directory: if they're cropped as
expected, then they're ready to be uploaded.

### Optimizing and uploading images

Cropped, full-resolution scans are stored as PNG images in the `scans` directory.
Before images are uploaded, we convert them to compressed JPG images, and we also
generate a small thumbnail image for each `a` image: e.g. `0053_a.jpg` will be resized
to generate `0053_thumb.jpg`.

These compressed JPG images are stored locally in a directory called `storage`, which
mirrors the layout of the S3-compatible bucket (in DigitalOcean Spaces) to which the
files are uploaded to be served to end-users.

Once you've scanned and cropped a new set of images for a batch of tapes, you can use
the [`upload.py`](./upload.py) script to upload the new images to a DigitalOcean Spaces
bucket, using the S3 API. Simply run:

- `python upload.py`

First, the script will identify any new images in `scans` that haven't yet been copied
to `storage`, and it will generate the requisite JPG images (including thumbnails) and
write them to `storage`.

Next, the script will compare the md5 hashes of all files in `storage` against the
hashes of all files in the bucket. Any JPG files that are new or modified will then be
uploaded to the bucket. Once the upload script completes successfully, all scanned and
cropped images are now synced to the Spaces bucket.

### Assigning a color to each tape

The tapes API associated a hex-formatted, RGB color value with each tape, so that the
app can display an appropriately-colored placeholder prior to loading the tape
thumbnail. The color for each tape is computed from the dominant color in the thumbnail
image, and these color values are stored in a "Color" column in the inventory
spreadsheet.

To assign colors to a new bach of tapes:

1. Ensure that all tapes have their images scanned, cropped, and uploaded.
2. Run `python get-color.py <tape-id>`, substituting the ID of the first tape in the
   batch.
3. Copy the resulting hex values to the clipboard.
4. In the [Golden VCR Inventory](https://docs.google.com/spreadsheets/d/1cR9Lbw9_VGQcEn8eGD2b5MwGRGzKugKZ9PVFkrqmA7k/edit),
   select the **Color** cell in the row for the starting tape, then paste the color
   values.
