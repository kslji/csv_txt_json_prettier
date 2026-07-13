from __future__ import annotations

from app.utils.constants import MAX_INPUT_SIZE_BYTES


class InputValidationError(Exception):
    def __init__(self, message: str, code: str = "invalid_input"):
        self.message = message
        self.code = code
        super().__init__(message)


def validate_and_decode(data: bytes) -> str:
    """
    Validates raw uploaded/pasted bytes and decodes to text.
    Pure deterministic checks: size limit + UTF-8 decodability.
    """
    if not data:
        raise InputValidationError("Input content is empty.", "empty_input")

    if len(data) > MAX_INPUT_SIZE_BYTES:
        mb = MAX_INPUT_SIZE_BYTES / (1024 * 1024)
        raise InputValidationError(
            f"Input exceeds the {mb:.0f}MB size limit.", "input_too_large"
        )

    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise InputValidationError(
                "Content could not be decoded as UTF-8 text.", "invalid_encoding"
            ) from exc
