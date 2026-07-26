output "policy_arn" {
  value = aws_iam_policy.media_signer.arn
}

output "policy_json" {
  value = data.aws_iam_policy_document.media_signer.json
}
