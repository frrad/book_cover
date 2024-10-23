import tempfile
from PIL import Image
from typing import List
import pikepdf
from decimal import Decimal


def split_book_cover(image: Image.Image, back_width: int, front_width: int):
    """
    Split an image containing a book cover into its back, spine, and front sections.

    Args:
    - image (Image): The input image containing the full book cover.
    - back_width (int): The width of the back cover.
    - front_width (int): The width of the front cover.

    Returns:
    - (back_img, spine_img, front_img): Tuple of Images for back page, spine, and front page.
    """
    original_width, original_height = image.size

    # Calculate spine width based on the provided back and front widths
    spine_width = original_width - back_width - front_width
    front_offset = original_width - front_width

    # Step 1: Crop the "back" page from the image
    back_crop_area = (0, 0, back_width, original_height)
    back_img = image.crop(back_crop_area)

    # Step 2: Crop the "spine" from the image
    spine_crop_area = (back_width, 0, back_width + spine_width, original_height)
    spine_img = image.crop(spine_crop_area)

    # Step 3: Crop the "front" page from the image
    front_crop_area = (front_offset, 0, original_width, original_height)
    front_img = image.crop(front_crop_area)

    return back_img, spine_img, front_img


def add_stretched_border(
    image: Image.Image, border_size_px: int, stretch_pixel_width: int = 1
) -> Image.Image:
    """
    Adds a border of the specified pixel size around the image
    by stretching the outermost rows and columns of specified width.

    Args:
        image (PIL.Image.Image): The input image to which the border will be added.
        border_size_px (int): The size of the border in pixels to be added to each side.
        stretch_pixel_width (int): Number of pixels to take from the edges to stretch (default 1 pixel).

    Returns:
        PIL.Image.Image: A new image with the stretched border.
    """

    # Get the size of the original image
    width, height = image.size

    # Ensure the stretch pixel width is not larger than image dimensions.
    stretch_pixel_width = min(stretch_pixel_width, width, height)

    # Create the border by extending the outermost pixels
    # Left pixel column(s)
    left_border = image.crop((0, 0, stretch_pixel_width, height)).resize(
        (border_size_px, height)
    )
    # Right pixel column(s)
    right_border = image.crop((width - stretch_pixel_width, 0, width, height)).resize(
        (border_size_px, height)
    )
    # Top pixel row(s)
    top_border = image.crop((0, 0, width, stretch_pixel_width)).resize(
        (width, border_size_px)
    )
    # Bottom pixel row(s)
    bottom_border = image.crop((0, height - stretch_pixel_width, width, height)).resize(
        (width, border_size_px)
    )

    # Create a new image with a larger size to fit the border
    new_width = width + 2 * border_size_px
    new_height = height + 2 * border_size_px
    new_image = Image.new("RGB", (new_width, new_height))

    # Paste the original image into the center of the new image
    new_image.paste(image, (border_size_px, border_size_px))

    # Paste the stretched borders
    new_image.paste(left_border, (0, border_size_px))  # Left border
    new_image.paste(
        right_border, (new_width - border_size_px, border_size_px)
    )  # Right border
    new_image.paste(top_border, (border_size_px, 0))  # Top border
    new_image.paste(
        bottom_border, (border_size_px, new_height - border_size_px)
    )  # Bottom border

    # Fill the corner areas using corner pixels (top-left, top-right, bottom-left, bottom-right)
    new_image.paste(
        image.getpixel((0, 0)), (0, 0, border_size_px, border_size_px)
    )  # Top-left corner
    new_image.paste(
        image.getpixel((width - 1, 0)),
        (new_width - border_size_px, 0, new_width, border_size_px),
    )  # Top-right corner
    new_image.paste(
        image.getpixel((0, height - 1)),
        (0, new_height - border_size_px, border_size_px, new_height),
    )  # Bottom-left corner
    new_image.paste(
        image.getpixel((width - 1, height - 1)),
        (
            new_width - border_size_px,
            new_height - border_size_px,
            new_width,
            new_height,
        ),
    )  # Bottom-right corner

    return new_image


def concatenate_images_horizontally(images: List[Image.Image]) -> Image.Image:
    """
    Concatenates multiple Pillow Image objects (with the same height) horizontally (left to right).

    :param images: A list of Pillow Image objects to concatenate.
    :return: The concatenated image (Pillow Image object).
    """
    # Ensure all images have the same height
    heights = [img.height for img in images]
    if len(set(heights)) > 1:
        raise ValueError(
            "All images must have the same height to concatenate horizontally"
        )

    # Calculate the total width of the concatenated image
    total_width = sum(img.width for img in images)

    # All images have the same height, so we can take the height of the first image
    height = images[0].height

    # Create a new blank image with total width and common height
    concatenated_image = Image.new("RGB", (total_width, height))

    # Paste each image into the concatenated_image, positioning them side by side
    current_width = 0
    for img in images:
        concatenated_image.paste(img, (current_width, 0))
        current_width += img.width  # Move to the right for the next image

    # Return the concatenated image as a Pillow Image object
    return concatenated_image


def add_bleed_box(
    input_image: Image.Image,
    dpi: int,
    output_pdf_path: str,
    full_width_px: int,
    full_height_px: int,
    left_offset_px: int,
    bottom_offset_px: int,
    right_offset_px: int,
    top_offset_px,
):
    with tempfile.NamedTemporaryFile(suffix=".pdf") as temp_file:
        original_pdf_path = temp_file.name

        input_image.save(original_pdf_path, "PDF", resolution=dpi)

        # Open the existing PDF file
        with pikepdf.open(original_pdf_path) as pdf:
            assert len(pdf.pages) == 1
            page = pdf.pages[0]

            media_box = page.MediaBox

            # attempt to figure out scaling factor between px and pdf units
            media_box_width = media_box[2] - media_box[0]
            media_box_height = media_box[3] - media_box[1]
            unit_per_px = media_box_width / Decimal(full_width_px)
            print(unit_per_px)
            assert unit_per_px == media_box_height / Decimal(full_height_px)

            # Create a new BleedBox based on the provided offsets
            bleed_box = [
                media_box[0] + left_offset_px * unit_per_px,
                media_box[1] + top_offset_px * unit_per_px,
                media_box[2] - right_offset_px * unit_per_px,
                media_box[3] - bottom_offset_px * unit_per_px,
            ]

            page.bleedbox = bleed_box
            print(bleed_box)

            pdf.save(output_pdf_path)

        print(f"Bleed box added and saved to {output_pdf_path}")


def main(in_file_path: str):
    img = Image.open(in_file_path)

    back_img, spine_img, front_img = split_book_cover(
        img, back_width=1630, front_width=1625
    )

    dpi = 300

    target_height_in = 8.5
    target_width_in = 11 / 2.0
    target_spine_width = 0.65

    target_cover_width_px = int(target_width_in * dpi)
    target_height_px = int(target_height_in * dpi)
    target_spine_width_px = int(target_spine_width * dpi)

    cover_dims = (target_cover_width_px, target_height_px)
    spine_dims = (target_spine_width_px, target_height_px)

    front_scaled = front_img.resize(cover_dims)
    back_scaled = back_img.resize(cover_dims)
    spine_scaled = spine_img.resize(spine_dims)

    rescaled_all = concatenate_images_horizontally(
        [back_scaled, spine_scaled, front_scaled]
    )

    bleed_size_in = 0.125
    bleed_size_px = int(bleed_size_in * dpi)

    stretched = add_stretched_border(
        rescaled_all, bleed_size_px, stretch_pixel_width=10
    )

    back_with_bleed, spine_with_bleed, front_with_bleed = split_book_cover(
        stretched,
        back_width=target_cover_width_px + bleed_size_px,
        front_width=target_cover_width_px + bleed_size_px,
    )

    add_bleed_box(
        back_with_bleed,
        dpi,
        "back.pdf",
        full_width_px=target_cover_width_px + bleed_size_px,
        full_height_px=target_height_px + 2 * bleed_size_px,
        left_offset_px=bleed_size_px,
        bottom_offset_px=bleed_size_px,
        right_offset_px=0,
        top_offset_px=bleed_size_px,
    )

    add_bleed_box(
        spine_with_bleed,
        dpi,
        "spine.pdf",
        full_width_px=target_spine_width_px,
        full_height_px=target_height_px + 2 * bleed_size_px,
        left_offset_px=0,
        bottom_offset_px=bleed_size_px,
        right_offset_px=0,
        top_offset_px=bleed_size_px,
    )

    add_bleed_box(
        front_with_bleed,
        dpi,
        "front.pdf",
        full_width_px=target_cover_width_px + bleed_size_px,
        full_height_px=target_height_px + 2 * bleed_size_px,
        left_offset_px=0,
        bottom_offset_px=bleed_size_px,
        right_offset_px=bleed_size_px,
        top_offset_px=bleed_size_px,
    )
