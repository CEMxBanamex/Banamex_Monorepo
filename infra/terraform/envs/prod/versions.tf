terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.80, < 7.0"
    }
  }

  # El bucket se pasa al inicializar (terraform init -backend-config="bucket=...").
  backend "s3" {
    key          = "prod/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Proyecto = "dsa"
      Gestion  = "terraform"
      Env      = "prod"
    }
  }
}
