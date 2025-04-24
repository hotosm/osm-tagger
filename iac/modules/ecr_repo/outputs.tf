output "repository_url" {
  description = "URL of the ECR repository"
  value       = aws_ecr_repository.repo.repository_url
}

output "repository_arn" {
  description = "ARN of the ECR repository"
  value       = aws_ecr_repository.repo.arn
}

output "repository_name" {
  description = "Name of the ECR repository"
  value       = aws_ecr_repository.repo.name
}

output "repository_registry_id" {
  description = "Registry ID of the ECR repository"
  value       = aws_ecr_repository.repo.registry_id
}
