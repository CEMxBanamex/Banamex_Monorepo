# Bootstrap: crea solo el bucket donde vive el estado de Terraform de las demás raíces.
# Su propio estado es local (bootstrap/terraform.tfstate, ignorado por git): si se pierde, basta volver a aplicar;
# la creación del bucket detecta que ya existe y no hace nada.
terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.80, < 7.0"
    }
  }
}

variable "region" {
  description = "Región de AWS. El Learner Lab solo permite una."
  type        = string
  default     = "us-east-1"
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Proyecto = "dsa"
      Gestion  = "terraform"
    }
  }
}

data "aws_caller_identity" "actual" {}

locals {
  # El ID de la cuenta hace único el nombre y solo aparece en tiempo de ejecución, nunca en el repo.
  bucket = "dsa-tfstate-${data.aws_caller_identity.actual.account_id}"
}

# El Learner Lab niega s3:GetBucketObjectLockConfiguration con una SCP, y el recurso aws_s3_bucket la lee siempre
# al crear o refrescar (falla con AccessDenied). Por eso el bucket se crea con la CLI de AWS y Terraform solo lo lee
# con el data source (que no consulta Object Lock) y administra su configuración. No se borra con terraform destroy.
resource "terraform_data" "bucket_estado" {
  input = local.bucket

  provisioner "local-exec" {
    command     = <<-EOT
      if aws s3api head-bucket --bucket "$BUCKET" --region "$REGION" 2>/dev/null; then
        echo "El bucket $BUCKET ya existe."
      elif [ "$REGION" = "us-east-1" ]; then
        aws s3api create-bucket --bucket "$BUCKET" --region "$REGION"
      else
        aws s3api create-bucket --bucket "$BUCKET" --region "$REGION" --create-bucket-configuration LocationConstraint="$REGION"
      fi
      aws s3api put-bucket-tagging --bucket "$BUCKET" --region "$REGION" \
        --tagging 'TagSet=[{Key=Proyecto,Value=dsa},{Key=Gestion,Value=terraform}]'
    EOT
    interpreter = ["/bin/sh", "-c"]
    environment = {
      BUCKET = local.bucket
      REGION = var.region
    }
  }
}

data "aws_s3_bucket" "estado" {
  bucket = terraform_data.bucket_estado.output
}

resource "aws_s3_bucket_versioning" "estado" {
  bucket = data.aws_s3_bucket.estado.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "estado" {
  bucket = data.aws_s3_bucket.estado.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "estado" {
  bucket                  = data.aws_s3_bucket.estado.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

output "bucket" {
  description = "Nombre del bucket del estado. Se pasa a las demás raíces con -backend-config y TF_VAR_state_bucket."
  value       = data.aws_s3_bucket.estado.bucket
}
