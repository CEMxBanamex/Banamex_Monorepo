resource "aws_cognito_user_pool" "este" {
  name = var.nombre

  # Se inicia sesión con el correo, y Cognito lo verifica enviando un código.
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  username_configuration {
    case_sensitive = false # Ana@x.com y ana@x.com son la misma cuenta
  }

  password_policy {
    minimum_length                   = 8
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = false
    temporary_password_validity_days = 7
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # Correo por omisión de Cognito (sin SES): tiene un límite diario bajo, suficiente para el proyecto.
  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }

  # Nadie se registra solo: las cuentas las crea quien administra el pool y les asigna su grupo.
  admin_create_user_config {
    allow_admin_create_user_only = true
  }

  mfa_configuration   = "OFF"
  deletion_protection = "INACTIVE" # permite terraform destroy al cerrar el lab
}

resource "aws_cognito_user_group" "grupo" {
  for_each = toset(var.grupos)

  name         = each.value
  user_pool_id = aws_cognito_user_pool.este.id
}

# Cliente público para la SPA: sin secreto (no se puede guardar en el navegador), flujo de
# código de autorización. Cognito acepta PKCE cuando el cliente manda code_challenge.
resource "aws_cognito_user_pool_client" "frontend" {
  name         = "${var.nombre}-frontend"
  user_pool_id = aws_cognito_user_pool.este.id

  generate_secret = false

  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  supported_identity_providers         = ["COGNITO"]
  callback_urls                        = var.callback_urls
  logout_urls                          = var.logout_urls

  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
  ]

  # No revela si un correo está registrado o no.
  prevent_user_existence_errors = "ENABLED"
}

resource "aws_cognito_user_pool_domain" "este" {
  count = var.dominio_prefijo == null ? 0 : 1

  domain       = var.dominio_prefijo
  user_pool_id = aws_cognito_user_pool.este.id
}
