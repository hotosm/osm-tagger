
# NOTE: make sure all resources have the following tags:
# project=osm-tagger
# environment=dev

# VPC
data "aws_vpc" "main" {
  id = "vpc-ea28198f"
}

data "aws_subnet" "private" {
  count = 6
  id = element([
    "subnet-008efd1c836f87fea",
    "subnet-035d98f1778d2dbce",
    "subnet-063f08db8746b3a17",
    "subnet-0bec667f5d50ebc8c",
    "subnet-0cd0d84e0ece50263"
  ], count.index)
}

# ECR repositories
module "osm_tagger_repo" {
  source = "../../modules/ecr_repo"

  repository_name       = "osm-tagger"
  image_tag_mutability  = "MUTABLE"
  force_delete          = true
  image_retention_count = 30
  allowed_principals    = ["ecs-tasks.amazonaws.com"]

  tags = {
    project     = "osm-tagger"
    environment = "dev"
  }
}

module "ollama_repo" {
  source = "../../modules/ecr_repo"

  repository_name       = "custom-ollama"
  image_tag_mutability  = "MUTABLE"
  force_delete          = true
  image_retention_count = 30
  allowed_principals    = ["ecs-tasks.amazonaws.com"]

  tags = {
    project     = "osm-tagger"
    environment = "dev"
  }
}


# ECS Task Role
data "aws_iam_policy_document" "ecs_task_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ecs_task_role" {
  name               = "osm-tagger-ecs-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json

  tags = {
    project     = "osm-tagger"
    environment = "dev"
  }
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_policy" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# RDS
module "tagging_db" {
  source = "git::https://github.com/hotosm/terraform-aws-rds.git?ref=main"
  # source = "git::https://github.com/hotosm/terraform-aws-rds.git?ref=v1.0"

  vpc_id     = data.aws_vpc.main.id
  subnet_ids = data.aws_subnet.private[*].id

  database = {
    name            = "osm_tagger_tagging_db"
    admin_user      = "osmtaggeradmin"
    password_length = 32
    engine_version  = 16.6
    port            = 5432
  }

  ## RDS Module inputs
  serverless_capacity = {
    minimum = 1 # Lowest possible APU for Aurora Serverless
    maximum = 4 # Max APU to keep cost low for Stag
  }

  ## RDS Backup/Snapshot Config
  backup = {
    retention_days            = 7
    skip_final_snapshot       = true
    final_snapshot_identifier = "final"
  }

  # RDS Dev Deployment only.
  public_access       = false
  deletion_protection = true

  default_tags = {
    project     = "osm-tagger"
    environment = "dev"
  }

  deployment_environment = "dev"

  project_meta = {
    name       = "osm-tagger"
    short_name = "osm-tagger"
    version    = "0.1.0"
    url        = "github.com/hotosm/osm-tagger"
  }

  org_meta = {
    name       = "Humanitarian OpenStreetMap Team"
    short_name = "hotosm"
    url        = "hotosm.org"
  }
}

# Create ALB for ECS service
module "alb" {
  source = "git::https://github.com/hotosm/terraform-aws-alb.git?ref=v1.1"

  alb_name          = "osm-tagger-alb"
  target_group_name = "osm-tagger-tg"
  vpc_id            = data.aws_vpc.main.id
  alb_subnets       = data.aws_subnet.private[*].id
  app_port          = 8000 # Tagger API port

  health_check_path = "/api/health"
  ip_address_type   = "ipv4"

  default_tags = {
    project        = "osm-tagger"
    environment    = "dev"
    maintainer     = ""
    documentation  = ""
    cost_center    = ""
    IaC_Management = "Terraform"
  }

  acm_tls_cert_backend_arn = "arn:aws:acm:us-east-1:670261699094:certificate/1d74321b-1e5b-4e31-b97a-580deb39c539"
}

# ECS Service
module "ecs_cluster" {
  source = "../../modules/ecs_cluster"

  cluster_name = "osm-tagger-cluster"

  tags = {
    project     = "osm-tagger"
    environment = "dev"
  }
}

# ECS Service
resource "aws_cloudwatch_log_group" "osm_tagger" {
  name = "/ecs/osm-tagger"

  tags = {
    project     = "osm-tagger"
    environment = "dev"
  }
}

resource "aws_cloudwatch_log_group" "osm_tagger_ollama" {
  name = "/ecs/osm-tagger-ollama"

  tags = {
    project     = "osm-tagger"
    environment = "dev"
  }
}

resource "aws_security_group" "osm_tagger_service_sg" {
  name        = "osm-tagger-service-sg"
  description = "Security group for osm-tagger service"
  vpc_id      = data.aws_vpc.main.id

  # Allow inbound traffic from ALB
  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [module.alb.load_balancer_public_security_group]
  }

  # Allow all traffic between tasks in the security group
  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
  }

  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    project     = "osm-tagger"
    environment = "dev"
  }
}

module "ecs" {
  source = "git::https://github.com/fulton-ring/terraform-aws-ecs.git?ref=additional-containers"

  service_name = "osm-tagger"
  default_tags = {
    project        = "osm-tagger"
    environment    = "dev"
    maintainer     = ""
    documentation  = ""
    cost_center    = ""
    IaC_Management = "Terraform"
  }

  container_ephemeral_storage = 40

  container_settings = {
    service_name = "osm-tagger"
    app_port     = 8000
    image_url    = "ghcr.io/hotosm/osm-tagger/osm-tagger"
    image_tag    = var.app_image_tag
  }

  # Using 1 vCPU with 4GB RAM for API
  container_capacity = {
    cpu       = 4096  # 4 vCPU
    memory_mb = 16384 # 16GB RAM
  }

  # container_commands = ["uvicorn", "tagger.main:app", "--host", "0.0.0.0", "--port", "8000"]

  container_secrets = {
    DB_HOST = "${module.tagging_db.database_credentials}:host::"
    DB_PORT = "${module.tagging_db.database_credentials}:port::"
    # DB_NAME     = "${module.tagging_db.database_credentials}:dbname::"
    DB_NAME     = "${module.tagging_db.database_credentials}"
    DB_USER     = "${module.tagging_db.database_credentials}:username::"
    DB_PASSWORD = "${module.tagging_db.database_credentials}:password::"
  }
  # container_secrets = {
  #   DB_HOST     = "${module.tagging_db.database_config_as_ecs_inputs.POSTGRES_ENDPOINT}::"
  #   DB_PORT     = "${module.tagging_db.database_config_as_ecs_inputs.POSTGRES_PORT}::"
  #   DB_NAME     = "${module.tagging_db.database_config_as_ecs_inputs.POSTGRES_DB}::"
  #   DB_USER     = "${module.tagging_db.database_config_as_ecs_inputs.POSTGRES_USER}::"
  #   DB_PASSWORD = module.tagging_db.database_config_as_ecs_secrets_inputs[0]
  # }

  container_envvars = {
    AWS_REGION = "us-east-1"
  }

  # Second container for Ollama
  additional_container_definitions = [
    {
      name  = "ollama"
      image = "ghcr.io/hotosm/osm-tagger/osm-tagger-ollama:${var.ollama_image_tag}"
      # command = ["ollama", "serve"]
      cpu    = 4096
      memory = 16384
      portMappings = [
        {
          containerPort = 11434
          hostPort      = 11434
        }
      ]
      logConfiguration = {
        logdriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.osm_tagger_ollama.name
          awslogs-region        = "us-east-1"
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ]

  tasks_count = {
    desired_count   = 1
    min_healthy_pct = 50
    max_pct         = 200
  }

  log_configuration = {
    logdriver = "awslogs"
    options = {
      awslogs-group         = aws_cloudwatch_log_group.osm_tagger.name
      awslogs-region        = "us-east-1" # Replace with your region
      awslogs-stream-prefix = "ecs"
    }
  }

  container_cpu_architecture = "ARM64"
  # container_cpu_architecture = "X86_64"
  force_new_deployment = true
  task_role_arn        = aws_iam_role.ecs_task_role.arn

  load_balancer_settings = {
    enabled                 = true
    arn_suffix              = module.alb.load_balancer_arn_suffix
    target_group_arn        = module.alb.target_group_arn
    target_group_arn_suffix = module.alb.target_group_arn_suffix
    scaling_request_count   = 50
  }

  service_security_groups = [
    aws_security_group.osm_tagger_service_sg.id
  ]

  # Required networking settings
  aws_vpc_id       = data.aws_vpc.main.id
  service_subnets  = data.aws_subnet.private[*].id
  ecs_cluster_name = module.ecs_cluster.cluster_name
  ecs_cluster_arn  = module.ecs_cluster.cluster_arn
}

# Allow ECS execution role to pull images from ECR
data "aws_iam_policy_document" "ecr_read_access" {
  statement {
    actions = [
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
      "ecr:BatchCheckLayerAvailability"
    ]
    resources = [
      module.osm_tagger_repo.repository_arn,
      module.ollama_repo.repository_arn
    ]
  }
}

resource "aws_iam_policy" "ecr_read_access" {
  name   = "osm-tagger-ecr-read-access"
  policy = data.aws_iam_policy_document.ecr_read_access.json
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_ecr" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.ecr_read_access.arn
}

# NOTE: may need cloudwatch logging setup
# resource "aws_iam_role_policy_attachment" "ecs_task_execution_cloudwatch" {
#   role       = module.ecs.execution_role_arn
#   policy_arn = "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
# }

# IAM Policies for ECS Task
# Policy for Bedrock access
data "aws_iam_policy_document" "bedrock_access" {
  statement {
    actions = [
      "bedrock:InvokeModel"
    ]
    # TODO: restrict to Llama vision 90b
    # model id: meta.llama3-2-90b-instruct-v1:0
    resources = ["*"]
  }
}

resource "aws_iam_policy" "bedrock_access" {
  name   = "osm-tagger-bedrock-access"
  policy = data.aws_iam_policy_document.bedrock_access.json
}

resource "aws_iam_role_policy_attachment" "bedrock_access" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.bedrock_access.arn
}

# Policy for S3 access
data "aws_s3_bucket" "osm_tagger" {
  bucket = "hotosm-osm-tagger"
}

data "aws_iam_policy_document" "s3_access" {
  statement {
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket"
    ]
    resources = [
      data.aws_s3_bucket.osm_tagger.arn,
      "${data.aws_s3_bucket.osm_tagger.arn}/*"
    ]
  }
}

resource "aws_iam_policy" "s3_access" {
  name   = "osm-tagger-s3-access"
  policy = data.aws_iam_policy_document.s3_access.json
}

resource "aws_iam_role_policy_attachment" "s3_access" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.s3_access.arn
}

# Policy for Secrets Manager access
data "aws_iam_policy_document" "secrets_access" {
  statement {
    actions = [
      "secretsmanager:GetSecretValue"
    ]
    resources = [
      module.tagging_db.database_credentials
    ]
  }
}

resource "aws_iam_policy" "secrets_access" {
  name   = "osm-tagger-secrets-access"
  policy = data.aws_iam_policy_document.secrets_access.json
}

resource "aws_iam_role_policy_attachment" "secrets_access" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.secrets_access.arn
}
