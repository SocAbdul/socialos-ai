output "bucket_id" {
  value = aws_s3_bucket.media.id
}

output "bucket_arn" {
  value = aws_s3_bucket.media.arn
}

output "bucket_regional_domain_name" {
  value = aws_s3_bucket.media.bucket_regional_domain_name
}

output "kms_key_arn" {
  value     = aws_kms_key.media.arn
  sensitive = true
}

output "origin_access_control_id" {
  value = aws_cloudfront_origin_access_control.media.id
}

output "cloudfront_distribution_id" {
  value = aws_cloudfront_distribution.media.id
}

output "cloudfront_distribution_arn" {
  value = aws_cloudfront_distribution.media.arn
}

output "cloudfront_domain_name" {
  value = aws_cloudfront_distribution.media.domain_name
}

output "media_public_base_url" {
  value = "https://${aws_cloudfront_distribution.media.domain_name}"
}
