# ─── Networking Module Variables ───────────────────────────────────────────────

variable "project_name" {
  description = "Project name for resource tagging"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR block for the public subnet"
  type        = string
  default     = "10.0.1.0/24"
}

variable "private_subnet_a_cidr" {
  description = "CIDR block for private subnet A"
  type        = string
  default     = "10.0.10.0/24"
}

variable "private_subnet_b_cidr" {
  description = "CIDR block for private subnet B"
  type        = string
  default     = "10.0.11.0/24"
}

variable "my_ip" {
  description = "Your IP address for SSH access (CIDR, e.g. 203.0.113.50/32)"
  type        = string
}
