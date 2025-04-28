variable "app_image_tag" {
  description = "Tag for the OSM Tagger application container image"
  type        = string
  default     = "main"
}

variable "ollama_image_tag" {
  description = "Tag for the Ollama container image"
  type        = string
  default     = "main"
}
