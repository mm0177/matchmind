# ─── RDS Module Variables ─────────────────────────────────────────────────────

variable "project_name" {
  description = "Project name for resource tagging"
  type        = string
}

variable "instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.micro"
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "matchmaking"
}

variable "username" {
  description = "Master username"
  type        = string
  default     = "matchmind_user"
}

variable "password" {
  description = "Master password (min 8 chars)"
  type        = string
  sensitive   = true
}

variable "subnet_ids" {
  description = "List of subnet IDs for the DB subnet group (needs 2+ AZs)"
  type        = list(string)
}

variable "security_group_id" {
  description = "Security group ID to attach"
  type        = string
}
