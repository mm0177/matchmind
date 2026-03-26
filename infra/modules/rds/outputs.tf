# ─── RDS Module Outputs ───────────────────────────────────────────────────────

output "endpoint" {
  description = "RDS endpoint (host:port)"
  value       = aws_db_instance.postgres.endpoint
}

output "hostname" {
  description = "RDS hostname only (without port)"
  value       = aws_db_instance.postgres.address
}

output "database_url" {
  description = "Full DATABASE_URL for .env.prod (replace PASSWORD with actual)"
  value       = "postgresql+asyncpg://${var.username}:PASSWORD@${aws_db_instance.postgres.endpoint}/${var.db_name}"
  sensitive   = true
}
