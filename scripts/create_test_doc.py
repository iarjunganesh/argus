from PIL import Image, ImageDraw


def create_synthetic_passport() -> None:
    img = Image.new("RGB", (600, 400), color="#1a3a6b")
    draw = ImageDraw.Draw(img)

    draw.rectangle([20, 20, 580, 380], outline="gold", width=3)
    draw.text((30, 40), "SYNTHETIC PASSPORT", fill="gold")
    draw.text((30, 100), "Surname:    SYNTHETIC", fill="white")
    draw.text((30, 130), "Given Name: JANE", fill="white")
    draw.text((30, 160), "Nationality: DEU", fill="white")
    draw.text((30, 190), "DOB:         1985-03-22", fill="white")
    draw.text((30, 220), "Passport No: SYN8472910", fill="white")
    draw.text((30, 250), "Expiry:      2030-03-22", fill="white")
    draw.text((30, 310), "SYNTHETIC DOCUMENT - NOT REAL", fill="yellow")

    path = "data/synthetic/test_passport.png"
    img.save(path)
    print(f"Saved: {path}")


if __name__ == "__main__":
    create_synthetic_passport()
