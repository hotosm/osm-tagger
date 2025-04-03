variable "repository_name" {
  description = "Name of the ECR repository"
  type        = string
}

variable "image_tag_mutability" {
  description = "Image tag mutability setting for the repository"
  type        = string
  default     = "MUTABLE"

  validation {
    condition     = contains(["MUTABLE", "IMMUTABLE"], var.image_tag_mutability)
    error_message = "Image tag mutability must be either MUTABLE or IMMUTABLE"
  }
}

variable "force_delete" {
  description = "Whether to force delete the repository"
  type        = bool
  default     = false
}

variable "image_retention_count" {
  description = "Number of images to retain in the repository"
  type        = number
  default     = 30
}

variable "allowed_principals" {
  description = "List of AWS principals allowed to pull images"
  type        = list(string)
}

variable "tags" {
  description = "Tags to apply to the ECR repository"
  type        = map(string)
  default     = {}
}
