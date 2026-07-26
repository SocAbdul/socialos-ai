output "deploy_role_arn" {
  value = aws_iam_role.github_actions_deploy.arn
}

output "oidc_provider_arn" {
  value = local.oidc_provider_arn
}
