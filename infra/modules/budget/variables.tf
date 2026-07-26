variable "name_prefix" {
  description = "Resource name prefix."
  type        = string
}

variable "monthly_limit_usd" {
  description = "Monthly budget limit in USD."
  type        = number
}

variable "alert_email" {
  description = "Email address that receives AWS budget alerts."
  type        = string
}
