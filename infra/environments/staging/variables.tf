variable "aws_region" {
  description = "AWS deployment region."
  type        = string
  default     = "eu-west-1"
}

variable "media_bucket_name" {
  description = "Globally unique S3 media bucket name."
  type        = string
}

variable "media_cors_allowed_origins" {
  description = "Frontend origins allowed to upload media directly."
  type        = list(string)
}

variable "monthly_budget_limit_usd" {
  description = "Monthly staging budget limit in USD."
  type        = number
  default     = 25
}

variable "budget_alert_email" {
  description = "Email address that receives AWS budget alerts."
  type        = string
}

variable "github_repository" {
  description = "GitHub repository in owner/name form."
  type        = string
  default     = "SocAbdul/socialos-ai"
}

variable "existing_github_oidc_provider_arn" {
  description = "Optional existing GitHub Actions OIDC provider ARN for this AWS account."
  type        = string
  default     = null
}
