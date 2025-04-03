variable "cluster_name" {
  description = "Name of the ECS cluster"
  type        = string
}

variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
}

variable "capacity_provider" {
  description = "Capacity provider for the ECS cluster"
  type        = string
  default     = "FARGATE_SPOT"
}
