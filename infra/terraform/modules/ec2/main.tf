# AMI más reciente de Amazon Linux 2023 (x86_64), publicada por AWS en un parámetro público de SSM.
data "aws_ssm_parameter" "al2023" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

# En Learner Lab no se pueden crear roles: se lee el perfil que ya existe.
data "aws_iam_instance_profile" "lab" {
  name = var.instance_profile_name
}

locals {
  nombre = "${var.nombre}-${var.env}"

  # La etiqueta Env la usa SSM Run Command para elegir la instancia de cada ambiente.
  etiquetas = merge(
    {
      Name = local.nombre
      Env  = var.env
    },
    var.runner ? { Runner = "true" } : {}
  )
}

resource "aws_instance" "esta" {
  # El ID de una AMI pública no es secreto; nonsensitive evita que todo el plan se oculte.
  ami                         = nonsensitive(data.aws_ssm_parameter.al2023.value)
  instance_type               = var.instance_type
  subnet_id                   = var.subnet_id
  vpc_security_group_ids      = [var.security_group_id]
  iam_instance_profile        = data.aws_iam_instance_profile.lab.name
  associate_public_ip_address = true # sale a internet sin NAT Gateway

  user_data                   = var.user_data
  user_data_replace_on_change = false # cambiar el script no debe recrear la instancia

  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.volume_gb
    encrypted             = true
    delete_on_termination = true
  }

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required" # IMDSv2 obligatorio
    # Salto 2: los contenedores de Docker están un salto de red más lejos y necesitan
    # leer las credenciales del perfil de la instancia desde IMDS.
    http_put_response_hop_limit = 2
  }

  tags        = local.etiquetas
  volume_tags = local.etiquetas

  lifecycle {
    # El parámetro de SSM cambia con cada AMI nueva; sin esto Terraform recrearía la instancia
    # (y perdería el disco). La AMI se actualiza a propósito, no en cada plan.
    ignore_changes = [ami]
  }
}

# IP fija: el registro A del dominio no cambia cuando el lab detiene e inicia la instancia.
resource "aws_eip" "esta" {
  domain = "vpc"

  tags = {
    Name = local.nombre
    Env  = var.env
  }
}

resource "aws_eip_association" "esta" {
  instance_id   = aws_instance.esta.id
  allocation_id = aws_eip.esta.id
}
