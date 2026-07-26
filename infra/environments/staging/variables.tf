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
