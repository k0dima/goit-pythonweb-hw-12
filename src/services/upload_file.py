import cloudinary
import cloudinary.uploader


class UploadFileService:
    """Configure Cloudinary and upload user avatars."""

    def __init__(self, cloud_name, api_key, api_secret):
        """Configure Cloudinary credentials for subsequent uploads.

        Args:
            cloud_name (str): Cloudinary cloud name.
            api_key (str | int): Cloudinary API key.
            api_secret (str): Cloudinary API secret.
        """
        self.cloud_name = cloud_name
        self.api_key = api_key
        self.api_secret = api_secret
        cloudinary.config(
            cloud_name=self.cloud_name,
            api_key=self.api_key,
            api_secret=self.api_secret,
            secure=True,
        )

    @staticmethod
    def upload_file(file, email) -> str:
        """Upload an avatar and return its transformed public URL.

        Args:
            file (UploadFile): Image file received by the API.
            email (str): User email used to form the Cloudinary public ID.

        Returns:
            str: URL of the resized avatar image.
        """
        public_id = f"RestApp/{email}"
        r = cloudinary.uploader.upload(file.file, public_id=public_id, overwrite=True)
        src_url = cloudinary.CloudinaryImage(public_id).build_url(
            width=250, height=250, crop="fill", version=r.get("version")
        )
        return src_url
