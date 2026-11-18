# Ambiente prod: una EC2 con IP elástica, su bucket de archivos y sus parámetros de SSM.
# La red, los security groups y la base vienen de la raíz shared.

locals {
  env      = "prod"
  api_host = "api.${var.dominio}"
  frontend = "https://app.${var.dominio}"
  shared   = data.terraform_remote_state.shared.outputs

  # Script de la primera vez que arranca la EC2: deploy/user-data.sh con sus variables al inicio.
  # Solo corre al crear la instancia; cambiarlo después no la recrea (user_data_replace_on_change = false).
  user_data = join("\n", [
    "#!/bin/bash",
    "export DSA_ENV=${local.env}",
    "export AWS_REGION=${var.region}",
    "export GITHUB_REPO=${var.github_repo}",
    "export DEPLOY_REF=main",
    file("${path.module}/../../../../deploy/user-data.sh"),
  ])
}

data "terraform_remote_state" "shared" {
  backend = "s3"
  config = {
    bucket = var.state_bucket
    key    = "shared/terraform.tfstate"
    region = var.region
  }
}

module "ec2" {
  source = "../../modules/ec2"

  env               = local.env
  subnet_id         = local.shared.public_subnet_ids[0]
  security_group_id = local.shared.ec2_sg_ids[local.env]
  instance_type     = var.instance_type
  volume_gb         = var.volume_gb
  runner            = false
  user_data         = local.user_data
}

module "s3" {
  source = "../../modules/s3"

  env             = local.env
  allowed_origins = [local.frontend, "http://localhost:5173"]
  force_destroy   = var.s3_force_destroy
}

module "ssm" {
  source = "../../modules/ssm"

  prefijo = "/dsa/${local.env}"

  # Valores que pone Juan Pablo con la CLI (o deploy.sh, en el caso de image_tag). Terraform solo crea el lugar.
  # Las cadenas de conexión no van aquí: generar-env.sh las arma en la EC2 con db_host, db_port, db_name y las
  # contraseñas de /dsa/shared/db/<rol> que crea scripts/db/crear-bases.sh.
  manuales = {
    ollama_base_url = { tipo = "String", descripcion = "URL de Ollama en la laptop con GPU, por Tailscale (http://100.x.y.z:11434)." }
    image_tag       = { tipo = "String", descripcion = "Tag de las imágenes desplegadas. Lo escribe deploy.sh." }
  }

  # Valores que no son secretos y que Terraform conoce.
  gestionados = merge(
    {
      auth_mode           = var.auth_mode
      aws_region          = var.region
      s3_bucket           = module.s3.bucket
      cors_origins        = local.frontend
      mcp_url             = "http://mcp:8001/mcp"
      api_host            = local.api_host
      db_host             = local.shared.rds_address
      db_port             = tostring(local.shared.rds_port)
      db_name             = "dsa_${local.env}"
      image_registry      = var.image_registry
      embedding_proveedor = "ollama"
    },
    # Solo existen cuando shared se aplicó con enable_cognito = true (un parámetro String no puede estar vacío).
    local.shared.cognito_user_pool_id == null ? {} : {
      cognito_user_pool_id = local.shared.cognito_user_pool_id
      cognito_client_id    = local.shared.cognito_client_id
    }
  )
}
