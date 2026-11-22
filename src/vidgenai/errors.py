INVALID_URL = "INVALID_URL"
UNSUPPORTED_PLATFORM = "UNSUPPORTED_PLATFORM"
PRIVATE_OR_LOGIN_REQUIRED = "PRIVATE_OR_LOGIN_REQUIRED"
FFMPEG_MISSING = "FFMPEG_MISSING"
DOWNLOAD_FAILED = "DOWNLOAD_FAILED"
CONVERSION_FAILED = "CONVERSION_FAILED"


class VidgenError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def to_dict(self) -> dict[str, str]:
        return {
            "status": "error",
            "code": self.code,
            "message": self.message,
        }
