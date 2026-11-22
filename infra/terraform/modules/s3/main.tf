# El ID de cuenta hace único el nombre del bucket; solo se conoce en tiempo de ejecución.
data "aws_caller_identity" "actual" {}

locals {
  bucket = "${var.nombre}-${var.env}-archivos-${data.aws_caller_identity.actual.account_id}"
}

# El Learner Lab niega s3:GetBucketObjectLockConfiguration con una SCP, y el recurso aws_s3_bucket la lee siempre
# al crear o refrescar (falla con AccessDenied). Por eso el bucket se crea y se borra con la CLI de AWS, y Terraform
# lo lee con el data source (que no consulta Object Lock) y administra su configuración.
resource "terraform_data" "bucket" {
  # Lo que necesita el borrado: un provisioner de destroy solo puede leer self.
  input = {
    bucket        = local.bucket
    region        = var.region
    force_destroy = var.force_destroy
    tags          = "TagSet=[{Key=Proyecto,Value=dsa},{Key=Gestion,Value=terraform},{Key=Name,Value=${var.nombre}-${var.env}-archivos},{Key=Env,Value=${var.env}}]"
  }

  provisioner "local-exec" {
    command     = <<-EOT
      if aws s3api head-bucket --bucket "$BUCKET" --region "$REGION" 2>/dev/null; then
        echo "El bucket $BUCKET ya existe."
      elif [ "$REGION" = "us-east-1" ]; then
        aws s3api create-bucket --bucket "$BUCKET" --region "$REGION"
      else
        aws s3api create-bucket --bucket "$BUCKET" --region "$REGION" --create-bucket-configuration LocationConstraint="$REGION"
      fi
      aws s3api put-bucket-tagging --bucket "$BUCKET" --region "$REGION" --tagging "$TAGS"
    EOT
    interpreter = ["/bin/sh", "-c"]
    environment = {
      BUCKET = self.input.bucket
      REGION = self.input.region
      TAGS   = self.input.tags
    }
  }

  # Sin force_destroy, igual que aws_s3_bucket: S3 se niega a borrar un bucket con archivos.
  provisioner "local-exec" {
    when        = destroy
    command     = <<-EOT
      if [ "$FORZAR" = "true" ]; then
        aws s3 rb "s3://$BUCKET" --region "$REGION" --force
      else
        aws s3api delete-bucket --bucket "$BUCKET" --region "$REGION"
      fi
    EOT
    interpreter = ["/bin/sh", "-c"]
    environment = {
      BUCKET = self.input.bucket
      REGION = self.input.region
      FORZAR = tostring(self.input.force_destroy)
    }
  }
}

data "aws_s3_bucket" "este" {
  bucket = terraform_data.bucket.output.bucket
}

# Nada es público: el acceso es por URL prefirmada firmada con el perfil de la instancia.
resource "aws_s3_bucket_public_access_block" "este" {
  bucket = data.aws_s3_bucket.este.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "este" {
  bucket = data.aws_s3_bucket.este.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256" # SSE-S3: sin llaves KMS que administrar
    }
  }
}

# Desactiva las ACL: el dueño del bucket es dueño de todos los objetos.
resource "aws_s3_bucket_ownership_controls" "este" {
  bucket = data.aws_s3_bucket.este.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

# El navegador sube (PUT) y descarga (GET) directo a S3 con la URL prefirmada.
resource "aws_s3_bucket_cors_configuration" "este" {
  bucket = data.aws_s3_bucket.este.id

  cors_rule {
    allowed_methods = ["PUT", "GET"]
    allowed_origins = var.allowed_origins
    allowed_headers = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}
