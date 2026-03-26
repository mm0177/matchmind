# ─── RDS Module ───────────────────────────────────────────────────────────────
# Creates: DB subnet group + PostgreSQL 16 instance with backups

resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnet"
  subnet_ids = var.subnet_ids

  tags = { Name = "${var.project_name}-db-subnet" }
}

resource "aws_db_instance" "postgres" {
  identifier     = "${var.project_name}-db"
  engine         = "postgres"
  engine_version = "16"
  instance_class = var.instance_class

  allocated_storage     = 20
  max_allocated_storage = 50
  storage_type          = "gp3"

  db_name  = var.db_name
  username = var.username
  password = var.password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [var.security_group_id]

  # Backups and protection
  backup_retention_period   = 1
  backup_window             = "03:00-04:00"
  maintenance_window        = "sun:05:00-sun:06:00"
  deletion_protection       = true
  skip_final_snapshot       = true

  # Private only — reachable from EC2 via security group
  publicly_accessible = false
  multi_az            = false

  tags = { Name = "${var.project_name}-db" }
}
