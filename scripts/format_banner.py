from PIL import Image, ImageDraw, ImageOps

def apply_rounded_frame(
    image_path: str,
    radius: int = 32,
    border_width: int = 3,
    border_color: tuple = (63, 185, 80, 255)  # Verde institucional #3fb950
):
    """Aplica cantos transparentes reais e borda no arquivo PNG."""
    print(f"🖼️ Processando cantos arredondados em: {image_path}...")
    img = Image.open(image_path).convert("RGBA")
    width, height = img.size

    # 1. Cria a máscara para o canal Alpha
    mask = Image.new("L", (width, height), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.rounded_rectangle([(0, 0), (width, height)], radius=radius, fill=255)

    # 2. Aplica a transparência nos 4 cantos da imagem
    img.putalpha(mask)

    # 3. Desenha a moldura sólida perimétrica
    draw = ImageDraw.Draw(img)
    offset = border_width / 2
    draw.rounded_rectangle(
        [(offset, offset), (width - offset, height - offset)],
        radius=radius,
        outline=border_color,
        width=border_width
    )

    img.save(image_path, "PNG")
    print(f"✅ Moldura aplicada com sucesso! Raio: {radius}px | Borda: {border_width}px")

if __name__ == "__main__":
    apply_rounded_frame("assets/cerrado_urbano.png")