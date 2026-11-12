# Ambiente prod: una EC2 con IP elástica, su bucket de archivos y sus parámetros de SSM.
# La red, los security groups y la base vienen de la raíz shared.

locals {
  env      = "prod"
  api_host = "api.${var.dominio}"
  frontend = "https://app.${var.dominio}"
  shared   = data.terraform_remote_state.shared.outputs
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
  # user_data: lo conecta la Fase 4, cuando exista deploy/user-data.sh.
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
  manuales = {
    database_url             = { tipo = "SecureString", descripcion = "Conexión del backend (usuario steward_backend)." }
    mcp_database_url         = { tipo = "SecureString", descripcion = "Conexión del servidor MCP (usuario steward_mcp)." }
    consultas_database_url   = { tipo = "SecureString", descripcion = "Conexión de consulta libre (usuario steward_consultas)." }
    migraciones_database_url = { tipo = "SecureString", descripcion = "Conexión de las migraciones (usuario steward_migraciones)." }
    carga_database_url       = { tipo = "SecureString", descripcion = "Conexión de la carga de datos (usuario steward_carga)." }
    ollama_base_url          = { tipo = "String", descripcion = "URL de Ollama en la laptop con GPU, por Tailscale." }
    image_tag                = { tipo = "String", descripcion = "Tag de las imágenes desplegadas. Lo escribe deploy.sh." }
  }

  # Valores que no son secretos y que Terraform conoce.
  gestionados = merge(
    {
      auth_mode    = var.auth_mode
      aws_region   = var.region
      s3_bucket    = module.s3.bucket
      cors_origins = local.frontend
      mcp_url      = "http://mcp:8001/mcp"
      api_host     = local.api_host
      db_host      = local.shared.rds_address
      db_port      = tostring(local.shared.rds_port)
      db_name      = "dsa_${local.env}"
    },
    # Solo existen cuando shared se aplicó con enable_cognito = true (un parámetro String no puede estar vacío).
    local.shared.cognito_user_pool_id == null ? {} : {
      cognito_user_pool_id = local.shared.cognito_user_pool_id
      cognito_client_id    = local.shared.cognito_client_id
    }
  )
}
