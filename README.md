# image-tools

The **image-tools** repo contains and scripts that aid in the process of scanning and
cataloguing new tapes as they're added to the Golden VCR library. This is a largely
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

The [`renumber.sh`](./renumber.sh) script allows us to quickly rename tape images en
masse as we scan them. To get started scanning:

- Turn on your scanner, open the lid, and clean the glass if necessary.
- Open NAPS2.
- Open a file explorer window in the `scans` directory.
- Open a bash shell in the root of this repo.

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
4. In your bash shell, run `./renumber.sh -i <tape-id>`, where `<tape-id>` is the ID
   with which this tape has been labeled.
     - This should automatically rename the new images in your `scans` directory, e.g.
       from `scan_0001.png`, `scan_0002.png`, etc. to `0053_a.png`, `0053_b.png`, etc.
     - You can supply the `-n` flag to dry-run the command and preview the renames it
       would perform.
     - Once you have at least one set of renamed tape images in the scans directory,
       you can omit the `-i` argument: the script will continue numbering scans
       sequentially based on the highest-numbered tape images present in the directory.

Once you've scanned all the tapes that you previously catalogued, you can grab another
batch of tapes and add them to the spreadsheet. When you've finished scanning and are
ready to move on, then it's time to process your scanned images and get them ready for
upload.
