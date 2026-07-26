variable "name_prefix" {
  description = "Resource name prefix."
  type        = string
}

variable "repository_names" {
  description = "ECR repository suffixes."
  type        = set(string)
}

variable "tags" {
  description = "Tags applied to resources."
  type        = map(string)
  default     = {}
}
