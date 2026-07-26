variable "name_prefix" {
  description = "Resource name prefix."
  type        = string
}

variable "github_repository" {
  description = "GitHub repository in owner/name form."
  type        = string
}

variable "allowed_refs" {
  description = "GitHub refs allowed to assume the deployment role."
  type        = list(string)
}

variable "existing_oidc_provider_arn" {
  description = "Optional existing GitHub Actions OIDC provider ARN. Leave null to create one."
  type        = string
  default     = null
}

variable "ecr_repository_arns" {
  description = "ECR repository ARNs the role can push to."
  type        = list(string)
}

variable "tags" {
  description = "Tags applied to resources."
  type        = map(string)
  default     = {}
}
