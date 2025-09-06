from pathlib import Path

from bgremove import remove_file


def test_smoke_png():
    # Tiny 1x1 PNG with white pixel
    sample = Path(__file__).parent / "white1x1.png"
    if not sample.exists():
        # create one if missing
        import base64
        sample.write_bytes(base64.b64decode(
            b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAuMB9m0mM9YAAAAASUVORK5CYII="
        ))
    out = remove_file(str(sample))
    assert isinstance(out, (bytes, bytearray))
    assert out[:8] == b"\x89PNG\r\n\x1a\n"
