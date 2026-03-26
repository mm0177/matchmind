variable "aws_region" {
  description = "AWS region to deploy in"
  type        = string
  default     = "ap-south-1" # Mumbai — closest to India-based users
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "matchmind"
}

variable "ec2_instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.medium"
}

variable "ec2_key_pair_name" {
  description = "Name of an existing EC2 Key Pair for SSH access"
  type        = string
}

variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.micro"
}

variable "rds_db_name" {
  description = "Database name"
  type        = string
  default     = "matchmaking"
}

variable "rds_username" {
  description = "RDS master username"
  type        = string
  default     = "matchmind_user"
}

variable "rds_password" {
  description = "RDS master password (min 8 chars)"
  type        = string
  sensitive   = true
}

variable "my_ip" {
  description = "Your IP address for SSH access (e.g. 203.0.113.50/32). Find it at whatismyip.com"
  type        = string
}
