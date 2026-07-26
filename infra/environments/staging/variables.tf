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

variable "vpc_cidr" {
  description = "CIDR block for the staging VPC."
  type        = string
  default     = "10.40.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "Public subnet CIDRs for the low-cost staging runtime."
  type        = list(string)
  default     = ["10.40.1.0/24", "10.40.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "Private isolated subnet CIDRs for staging data services."
  type        = list(string)
  default     = ["10.40.101.0/24", "10.40.102.0/24"]
}

variable "staging_api_image" {
  description = "Immutable API image reference to deploy to staging ECS."
  type        = string
}

variable "staging_web_image" {
  description = "Immutable web image reference to deploy to staging ECS."
  type        = string
}

variable "staging_desired_count" {
  description = "Desired ECS task count per staging service."
  type        = number
  default     = 1
}

variable "staging_api_environment" {
  description = "Additional non-secret API environment variables."
  type        = map(string)
  default     = {}
}

variable "staging_web_environment" {
  description = "Additional non-secret web environment variables."
  type        = map(string)
  default     = {}
}

variable "staging_api_secret_arns" {
  description = "API secret environment variables mapped to SSM or Secrets Manager ARNs."
  type        = map(string)
  default     = {}
}

variable "staging_web_secret_arns" {
  description = "Web secret environment variables mapped to SSM or Secrets Manager ARNs."
  type        = map(string)
  default     = {}
}

variable "staging_secret_kms_key_arns" {
  description = "Optional KMS key ARNs required to decrypt staging runtime secrets."
  type        = set(string)
  default     = []
}

variable "staging_postgres_instance_class" {
  description = "RDS PostgreSQL instance class for staging."
  type        = string
  default     = "db.t4g.micro"
}

variable "staging_postgres_allocated_storage_gb" {
  description = "RDS PostgreSQL allocated storage in GiB for staging."
  type        = number
  default     = 20
}

variable "staging_postgres_backup_retention_days" {
  description = "RDS PostgreSQL automated backup retention in days for staging."
  type        = number
  default     = 7
}

variable "staging_redis_node_type" {
  description = "ElastiCache Redis node type for staging."
  type        = string
  default     = "cache.t4g.micro"
}
