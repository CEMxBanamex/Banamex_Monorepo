# Infraestructura en AWS (Terraform)

Todo lo que el proyecto tiene en AWS se crea desde aquí. La cuenta es de **Learner Lab**: no se pueden crear recursos de IAM (las EC2 usan `LabInstanceProfile`), las credenciales cambian en cada sesión y los créditos son pocos.

## Qué se crea

```
Internet
 ├── api-dev.<DOMINIO> ── registro A ──► IP elástica ──► EC2 dev  (Caddy 80/443 → backend, mcp, runner de GitHub)
 └── api.<DOMINIO>     ── registro A ──► IP elástica ──► EC2 prod (Caddy 80/443 → backend, mcp)

VPC /16, 2 zonas, sin NAT, endpoint de S3
 Subredes públicas: las dos EC2 y RDS (pública solo hasta el cierre)
 RDS PostgreSQL 16 db.t4g.micro: bases dsa_dev y dsa_prod, SSL obligatorio
S3: un bucket privado por ambiente · SSM Parameter Store: /dsa/<env>/... · Budgets · Cognito (al final)
```

No hay balanceador ni certificado de ACM: el HTTPS lo da **Caddy** en cada EC2 con un certificado de Let's Encrypt, y una IP elástica mantiene fijo el registro A del dominio. Se eligió así para cuidar los créditos.

## Estructura

| Carpeta | Qué contiene | Estado |
|---|---|---|
| `bootstrap/` | El bucket del estado de Terraform | Local (`bootstrap/terraform.tfstate`, no se versiona) |
| `envs/shared/` | VPC, security groups, RDS, presupuesto, Cognito y parámetros comunes | `shared/terraform.tfstate` en el bucket |
| `envs/dev/` | EC2 con IP elástica, bucket de archivos y parámetros de SSM de dev | `dev/terraform.tfstate` |
| `envs/prod/` | Lo mismo para prod | `prod/terraform.tfstate` |
| `modules/` | `network`, `security`, `rds`, `budget`, `ec2`, `s3`, `ssm`, `cognito` | — |

`dev` y `prod` leen los outputs de `shared` con `terraform_remote_state`, así que `shared` se aplica primero.

## Antes de empezar

1. Enciende el lab y copia sus credenciales a `~/.aws/credentials` (cambian en cada sesión). Comprueba con `aws sts get-caller-identity`. Si un comando falla con `ExpiredToken`, vuelve a copiarlas.
2. En cada raíz de `envs/`, copia `terraform.tfvars.example` a `terraform.tfvars` y pon los valores reales. Los `.tfvars` no se versionan.

## Orden de aplicación

Cada bloque se corre desde `infra/terraform/`. Revisa siempre el `plan` antes de aplicar.

```bash
# 1. Bucket del estado (una sola vez)
terraform -chdir=bootstrap init
terraform -chdir=bootstrap apply
export TF_STATE_BUCKET="$(terraform -chdir=bootstrap output -raw bucket)"

# 2. Recursos compartidos
terraform -chdir=envs/shared init -backend-config="bucket=$TF_STATE_BUCKET"
terraform -chdir=envs/shared plan -out=shared.tfplan
terraform -chdir=envs/shared apply shared.tfplan

# 3. dev (y prod más adelante, igual pero con envs/prod)
terraform -chdir=envs/dev init -backend-config="bucket=$TF_STATE_BUCKET"
terraform -chdir=envs/dev plan -var="state_bucket=$TF_STATE_BUCKET" -out=dev.tfplan
terraform -chdir=envs/dev apply dev.tfplan
```

Después de aplicar `dev` o `prod`:

1. `terraform -chdir=envs/dev output registro_dns` dice qué **registro A** crear en el registrador del dominio.
2. Los parámetros de SSM que quedaron con el valor `CAMBIAR` se llenan con la CLI, por ejemplo:
   ```bash
   aws ssm put-parameter --overwrite --type SecureString --name /dsa/dev/database_url --value '<CADENA-DE-CONEXION>'
   ```
   Terraform no vuelve a tocar esos valores.

## Cuidar los créditos

| Recurso | Cobra con el lab apagado |
|---|---|
| IP elásticas (una por EC2) | Sí |
| Discos de las EC2 y de RDS | Sí |
| Secreto de la contraseña maestra de RDS | Sí |
| EC2 y RDS encendidas | No |

- No apliques `prod` hasta que haga falta para el despliegue.
- El presupuesto manda correos al llegar a 8, 14 y 20 USD de gasto real (variables `presupuesto_*` de `shared`).
- El panel de créditos del lab se actualiza con horas de retraso.

## Cierre del 24 de noviembre

Solo cambian variables; nada se recrea.

- En `envs/shared/terraform.tfvars`: `db_publica = false`, `db_allowed_cidrs = []`, `enable_cognito = true`, `cognito_dominio_prefijo` y `allowed_cidrs_prod = ["0.0.0.0/0"]`.
- En `envs/prod/terraform.tfvars`: `auth_mode = "cognito"`.
- Aplica `shared` y después `prod` (y `dev`, para que reciba los datos de Cognito).

## Si la cuenta del lab se reinicia

Se pierde todo lo que hay en AWS, incluido el bucket del estado. Borra `bootstrap/terraform.tfstate*` y las carpetas `.terraform/`, y repite el orden de aplicación desde el paso 1. Las IP elásticas cambian: actualiza los registros A.

## Validar sin aplicar

```bash
terraform fmt -check -recursive
for raiz in bootstrap envs/shared envs/dev envs/prod; do
  terraform -chdir="$raiz" init -backend=false -input=false > /dev/null && terraform -chdir="$raiz" validate
done
grep -rn 'resource "aws_iam_' . --include=*.tf   # no debe encontrar nada
```
