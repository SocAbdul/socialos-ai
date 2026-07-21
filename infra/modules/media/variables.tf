variable "name_prefix" {
  description = "Resource name prefix."
  type        = string
}

variable "bucket_name" {
  description = "Globally unique S3 media bucket name."
  type        = string
}

variable "tags" {
  description = "Tags applied to all resources."
  type        = map(string)
  default     = {}
}

