#!/bin/bash

dry_run=false
new_image_number=0
verbose=false
images_dir="scans"  # Default value

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -n|--dry-run)
            dry_run=true
            shift
            ;;
        -i|--image-num)
            if [[ $2 =~ ^[0-9]+$ ]]; then
                new_image_number=$2
                shift 2
            else
                echo "Error: Invalid value for -i/--image-num argument. Please provide a valid integer."
                exit 1
            fi
            ;;
        -v|--verbose)
            verbose=true
            shift
            ;;
        *)
            # Treat the first positional argument as the target directory
            images_dir="$1"
            shift
            ;;
    esac
done

# Ensure the target directory exists
if [ ! -d "$images_dir" ]; then
    echo "Error: The specified directory '$images_dir' does not exist."
    exit 1
fi

# Change to the target directory
cd "$images_dir" || exit 1

# Task 1: List all 'scan_' files with a .png extension in alphabetical order
input_files=($(ls -1 scan_*.png 2>/dev/null | sort))

# Check if there are no valid input files
if [ ${#input_files[@]} -eq 0 ]; then
    echo "No files to rename."
    exit 0
fi

# Task 3: Compute the new image number by adding 1 to the max image number (if not explicitly set)
if [ $new_image_number -eq 0 ]; then
    max_image_number=0
    
    # List all files with names beginning with four digits followed by an underscore
    existing_image_files=($(ls -1 [0-9][0-9][0-9][0-9]_* 2>/dev/null | sort))
    
    for file in ${existing_image_files[@]}; do
        # Extract the 4-digit integer part from the filename and remove leading zeroes
        number=$(echo "$file" | grep -oP '\d{4}' | sed 's/^0*//')
        
        # Check if the extracted part is a valid integer
        if [[ $number =~ ^[0-9]{1,4}$ ]]; then
            if $verbose; then
                echo "File $file has number $number."
            fi
            # Update max_image_number if this number is greater
            if ((number > max_image_number)); then
                if $verbose; then
                    echo "Updating max_image_number from $max_image_number to $number."
                fi
                max_image_number=$number
            fi
        fi
    done
    new_image_number=$((max_image_number + 1))
fi

# Task 4: Rename the input files
increment_char='a'
for file in ${input_files[@]}; do
    # Create the new filename
    new_filename=$(printf "%04d_%s.png" "$new_image_number" "$increment_char")
    
    if [ -e "$new_filename" ]; then
        echo "ERROR: $new_filename already exists."
        exit 1
    fi
    
    if $dry_run; then
        # Print the 'mv' command for dry-run
        echo "Dry run: mv \"$file\" \"$new_filename\""
    else
        # Rename the file
        mv "$file" "$new_filename"
        echo "Renamed: $file -> $new_filename"
    fi
    
    # Increment the character for the next file
    increment_char=$(echo -e "$increment_char" | tr "a-z" "b-z_")
done

if $dry_run; then
    echo "Dry-run completed. No files were renamed."
else
    echo "Files renamed successfully."
fi
