variable "name_prefix" {
  description = "Resource name prefix."
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets."
  type        = list(string)

  validation {
    condition     = length(var.public_subnet_cidrs) >= 2
    error_message = "At least two public subnets are required for an internet-facing load balancer."
  }
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private isolated subnets."
  type        = list(string)
  default     = []

  validation {
    condition = (
      length(var.private_subnet_cidrs) == 0 ||
      length(var.private_subnet_cidrs) >= 2
    )
    error_message = "Private subnet CIDRs must be empty or include at least two subnets."
  }
}

variable "tags" {
  description = "Tags applied to resources."
  type        = map(string)
  default     = {}
}
