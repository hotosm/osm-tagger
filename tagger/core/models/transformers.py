import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoImageProcessor
from PIL import Image
import base64
from io import BytesIO
from typing import List

from tagger.core.models.interface import VisionEmbeddingModel


class NomicVisionEmbeddingModel(VisionEmbeddingModel):
    def __init__(self):
        self.processor = AutoImageProcessor.from_pretrained(
            "nomic-ai/nomic-embed-vision-v1.5"
        )
        self.vision_model = AutoModel.from_pretrained(
            "nomic-ai/nomic-embed-vision-v1.5", trust_remote_code=True
        )

    def image_embedding(self, images_base64: List[str]) -> List[List[float]]:
        # Convert base64 strings to PIL Images
        images = []
        for image_base64 in images_base64:
            image_bytes = base64.b64decode(image_base64)
            image = Image.open(BytesIO(image_bytes))
            images.append(image)

        # Process images in batch
        inputs = self.processor(images, return_tensors="pt")

        # Get embeddings for all images at once
        with torch.no_grad():
            img_emb = self.vision_model(**inputs).last_hidden_state
            img_embeddings = F.normalize(img_emb[:, 0], p=2, dim=1)

        # Convert to list of lists
        return img_embeddings.tolist()
