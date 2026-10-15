"""Generate synthetic test wine bottle image fixture for testing."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def create_fixture_image(output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 400x800 bottle image
    img = Image.new("RGB", (400, 800), color=(245, 240, 235))
    draw = ImageDraw.Draw(img)

    # Bottle silhouette / burgundy body
    draw.rectangle([60, 100, 340, 780], fill=(55, 12, 24))  # Deep burgundy bottle glass

    # Cream wine label
    draw.rectangle([90, 280, 310, 620], fill=(255, 253, 245), outline=(180, 150, 100), width=2)

    # Text elements on label
    draw.text((120, 310), "CHÂTEAU LYNCH-BAGES", fill=(30, 30, 30))
    draw.text((140, 360), "PAUILLAC", fill=(80, 20, 30))
    draw.text((125, 400), "GRAND CRU CLASSÉ", fill=(100, 80, 50))
    draw.text((180, 450), "2018", fill=(30, 30, 30))
    draw.text((115, 520), "Mis en bouteille au château", fill=(120, 120, 120))
    draw.text((105, 560), "14.5% vol.          750 ml", fill=(80, 80, 80))

    img.save(output_path, format="JPEG", quality=90)
    print(f"Created fixture image at {output_path}")


if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "sample_bottle.jpg"
    create_fixture_image(target)
