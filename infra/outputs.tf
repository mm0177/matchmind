# ─── Outputs ──────────────────────────────────────────────────────────────────
# Printed after `terraform apply` — use these to configure .env.prod

output "ec2_public_ip" {
  description = "Elastic IP — point your domain A record here"
  value       = module.ec2.public_ip
}

output "ec2_ssh_command" {
  description = "SSH into the EC2 instance"
  value       = module.ec2.ssh_command
}

output "rds_endpoint" {
  description = "RDS endpoint (host:port) — use in DATABASE_URL"
  value       = module.rds.endpoint
}

output "rds_database_url" {
  description = "Pre-formatted DATABASE_URL (replace PASSWORD)"
  value       = module.rds.database_url
  sensitive   = true
}

output "vpc_id" {
  description = "VPC ID"
  value       = module.networking.vpc_id
}
