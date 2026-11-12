# El ID de cuenta hace único el nombre del bucket; solo se conoce en tiempo de ejecución.
data "aws_caller_identity" "actual" {}

resource "aws_s3_bucket" "este" {
  bucket        = "${var.nombre}-${var.env}-archivos-${data.aws_caller_identity.actual.account_id}"
  force_destroy = var.force_destroy

  tags = {
    Name = "${var.nombre}-${var.env}-archivos"
    Env  = var.env
  }
}

# Nada es público: el acceso es por URL prefirmada firmada con el perfil de la instancia.
resource "aws_s3_bucket_public_access_block" "este" {
  bucket = aws_s3_bucket.este.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "este" {
  bucket = aws_s3_bucket.este.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256" # SSE-S3: sin llaves KMS que administrar
    }
  }
}

# Desactiva las ACL: el dueño del bucket es dueño de todos los objetos.
resource "aws_s3_bucket_ownership_controls" "este" {
  bucket = aws_s3_bucket.este.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

# El navegador sube (PUT) y descarga (GET) directo a S3 con la URL prefirmada.
resource "aws_s3_bucket_cors_configuration" "este" {
  bucket = aws_s3_bucket.este.id

  cors_rule {
    allowed_methods = ["PUT", "GET"]
    allowed_origins = var.allowed_origins
    allowed_headers = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}
