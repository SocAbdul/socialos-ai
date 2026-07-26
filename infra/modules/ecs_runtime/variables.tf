variable "name_prefix" {
  description = "Resource name prefix."
  type        = string
}

variable "vpc_id" {
  description = "VPC ID for the runtime."
  type        = string
}

variable "subnet_ids" {
  description = "Subnet IDs for the ALB and Fargate services."
  type        = list(string)
}

variable "api_image" {
  description = "Immutable API container image reference."
  type        = string
}

variable "web_image" {
  description = "Immutable web container image reference."
  type        = string
}

variable "api_environment" {
  description = "Plaintext API environment variables. Do not put secrets here."
  type        = map(string)
  default     = {}
}

variable "web_environment" {
  description = "Plaintext web environment variables. Do not put secrets here."
  type        = map(string)
  default     = {}
}

variable "api_secrets" {
  description = "API secrets as environment variable name to SSM/Secrets Manager ARN."
  type        = map(string)
  default     = {}
}

variable "web_secrets" {
  description = "Web secrets as environment variable name to SSM/Secrets Manager ARN."
  type        = map(string)
  default     = {}
}

variable "task_policy_arns" {
  description = "Additional IAM policy ARNs attached to the ECS task role."
  type        = set(string)
  default     = []
}

variable "secret_kms_key_arns" {
  description = "Optional KMS key ARNs required to decrypt injected ECS secrets."
  type        = set(string)
  default     = []
}

variable "desired_count" {
  description = "Desired task count per service."
  type        = number
  default     = 1
}

variable "api_cpu" {
  description = "API task CPU units."
  type        = number
  default     = 512
}

variable "api_memory" {
  description = "API task memory in MiB."
  type        = number
  default     = 1024
}

variable "web_cpu" {
  description = "Web task CPU units."
  type        = number
  default     = 512
}

variable "web_memory" {
  description = "Web task memory in MiB."
  type        = number
  default     = 1024
}

variable "enable_container_insights" {
  description = "Enable ECS Container Insights."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags applied to resources."
  type        = map(string)
  default     = {}
}
