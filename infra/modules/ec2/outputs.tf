# ─── EC2 Module Outputs ───────────────────────────────────────────────────────

output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.app.id
}

output "public_ip" {
  description = "Elastic IP address — point your domain A record here"
  value       = aws_eip.app.public_ip
}

output "ssh_command" {
  description = "SSH command to connect"
  value       = "ssh -i your-key.pem ec2-user@${aws_eip.app.public_ip}"
}
