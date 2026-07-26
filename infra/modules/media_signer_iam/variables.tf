variable "name_prefix" {
  description = "Resource name prefix."
  type        = string
}

variable "media_bucket_arn" {
  description = "Media bucket ARN."
  type        = string
}

variable "kms_key_arn" {
  description = "Media KMS key ARN."
  type        = string
}

variable "tags" {
  description = "Tags applied to resources."
  type        = map(string)
  default     = {}
}
