locals {
  # Familia del parameter group según la versión mayor ("16" o "16.x" => postgres16).
  familia = "postgres${split(".", var.engine_version)[0]}"
}

resource "aws_db_subnet_group" "este" {
  name       = "${var.nombre}-postgres"
  subnet_ids = var.subnet_ids

  tags = { Name = "${var.nombre}-postgres" }
}

resource "aws_db_parameter_group" "este" {
  name   = "${var.nombre}-${local.familia}"
  family = local.familia

  # Rechaza conexiones sin TLS (importante mientras la base sea pública).
  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }

  tags = { Name = "${var.nombre}-${local.familia}" }
}

# publicly_accessible se modifica en sitio (ModifyDBInstance), así que pasar
# db_publica de true a false no recrea la instancia; no hace falta lifecycle.
resource "aws_db_instance" "esta" {
  identifier = "${var.nombre}-postgres"

  engine         = "postgres"
  engine_version = var.engine_version
  instance_class = var.instance_class

  allocated_storage = var.allocated_storage
  storage_type      = "gp3"
  storage_encrypted = true

  # Sin db_name: dsa_dev y dsa_prod se crean después con un script.
  username                    = var.master_username
  manage_master_user_password = true

  db_subnet_group_name   = aws_db_subnet_group.este.name
  parameter_group_name   = aws_db_parameter_group.este.name
  vpc_security_group_ids = [var.security_group_id]
  publicly_accessible    = var.db_publica
  multi_az               = false

  backup_retention_period    = var.backup_retention_days
  copy_tags_to_snapshot      = true
  auto_minor_version_upgrade = true
  apply_immediately          = true

  # Entorno escolar: se puede destruir sin snapshot final.
  skip_final_snapshot = true
  deletion_protection = false

  # Enhanced Monitoring y Performance Insights requieren rol de IAM (no permitido en el lab).
  monitoring_interval          = 0
  performance_insights_enabled = false

  tags = { Name = "${var.nombre}-postgres" }
}
