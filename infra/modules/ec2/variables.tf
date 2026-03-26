# ─── EC2 Module Variables ─────────────────────────────────────────────────────

variable "project_name" {
  description = "Project name for resource tagging"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.medium"
}

variable "key_pair_name" {
  description = "Name of an existing EC2 Key Pair for SSH access"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID to launch the instance in"
  type        = string
}

variable "security_group_id" {
  description = "Security group ID to attach"
  type        = string
}

variable "user_data_path" {
  description = "Path to the user-data bootstrap script"
  type        = string
}
