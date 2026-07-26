output "endpoint" {
  value = aws_db_instance.this.address
}

output "port" {
  value = aws_db_instance.this.port
}

output "database_name" {
  value = var.database_name
}

output "security_group_id" {
  value = aws_security_group.this.id
}

output "database_url_secret_arn" {
  value = aws_secretsmanager_secret_version.database_url.arn
}
