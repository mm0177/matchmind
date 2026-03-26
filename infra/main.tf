# ─── MatchMind AWS Infrastructure ─────────────────────────────────────────────
# Modular Terraform setup: networking → ec2 → rds
#
# Usage:
#   cd infra
#   terraform init
#   terraform plan  -var-file="terraform.tfvars"
#   terraform apply -var-file="terraform.tfvars"
#
# Create infra/terraform.tfvars with your values (see variables.tf)

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ─── Module: Networking ───────────────────────────────────────────────────────
module "networking" {
  source = "./modules/networking"

  project_name = var.project_name
  my_ip        = var.my_ip
}

# ─── Module: EC2 ──────────────────────────────────────────────────────────────
module "ec2" {
  source = "./modules/ec2"

  project_name      = var.project_name
  instance_type     = var.ec2_instance_type
  key_pair_name     = var.ec2_key_pair_name
  subnet_id         = module.networking.public_subnet_id
  security_group_id = module.networking.ec2_security_group_id
  user_data_path    = "${path.module}/user-data.sh"
}

# ─── Module: RDS ──────────────────────────────────────────────────────────────
module "rds" {
  source = "./modules/rds"

  project_name      = var.project_name
  instance_class    = var.rds_instance_class
  db_name           = var.rds_db_name
  username          = var.rds_username
  password          = var.rds_password
  subnet_ids        = module.networking.private_subnet_ids
  security_group_id = module.networking.rds_security_group_id
}
