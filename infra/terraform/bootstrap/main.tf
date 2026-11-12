# Bootstrap: crea solo el bucket donde vive el estado de Terraform de las demás raíces.
# Su propio estado es local (bootstrap/terraform.tfstate, ignorado por git): si se pierde, el bucket se puede
# importar con `terraform import aws_s3_bucket.estado <nombre>`.
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

# El ID de la cuenta hace único el nombre y solo aparece en tiempo de ejecución, nunca en el repo.
resource "aws_s3_bucket" "estado" {
  bucket = "dsa-tfstate-${data.aws_caller_identity.actual.account_id}"
}

resource "aws_s3_bucket_versioning" "estado" {
  bucket = aws_s3_bucket.estado.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "estado" {
  bucket = aws_s3_bucket.estado.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "estado" {
  bucket                  = aws_s3_bucket.estado.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

output "bucket" {
  description = "Nombre del bucket del estado. Se pasa a las demás raíces con -backend-config y TF_VAR_state_bucket."
  value       = aws_s3_bucket.estado.bucket
}
