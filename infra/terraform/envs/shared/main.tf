# Recursos compartidos por dev y prod: red, security groups, base de datos, presupuesto y (al final) Cognito.

module "network" {
  source = "../../modules/network"
}

module "security" {
  source = "../../modules/security"

  vpc_id = module.network.vpc_id
  ambientes = {
    dev  = { allowed_cidrs = var.allowed_cidrs_dev }
    prod = { allowed_cidrs = var.allowed_cidrs_prod }
  }
  db_allowed_cidrs = var.db_allowed_cidrs
}

module "rds" {
  source = "../../modules/rds"

  # Subredes públicas mientras la base sea pública. El cierre es solo db_publica = false y db_allowed_cidrs = [].
  subnet_ids        = module.network.public_subnet_ids
  security_group_id = module.security.rds_sg_id
  db_publica        = var.db_publica
}

module "budget" {
  source = "../../modules/budget"

  limite_usd   = var.presupuesto_limite_usd
  umbrales_usd = var.presupuesto_umbrales_usd
  emails       = var.presupuesto_emails
}

module "cognito" {
  source = "../../modules/cognito"
  count  = var.enable_cognito ? 1 : 0

  callback_urls   = ["https://app.${var.dominio}/", "https://dev.${var.dominio}/", "http://localhost:5173/"]
  logout_urls     = ["https://app.${var.dominio}/", "https://dev.${var.dominio}/", "http://localhost:5173/"]
  dominio_prefijo = var.cognito_dominio_prefijo
}

# Parámetros comunes a los dos ambientes. Las contraseñas de los usuarios de la base (/dsa/shared/db/<usuario>)
# no se declaran aquí: las genera y guarda scripts/db/crear-bases.sh.
module "ssm" {
  source = "../../modules/ssm"

  prefijo = "/dsa/shared"
  manuales = {
    tailscale_authkey = {
      tipo        = "SecureString"
      descripcion = "Auth key de Tailscale (reutilizable, no efímera, tag:aws) con la que las EC2 se unen a la tailnet."
    }
  }
}
