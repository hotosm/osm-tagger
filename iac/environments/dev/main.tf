
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

# TODO: attachment to ALB, DNS, etc.

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

# TODO: create cloudwatch log groups for osm-tagger and ollama
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
    cpu       = 2048 # 2 vCPU
    memory_mb = 8192 # 8GB RAM
  }

  container_commands = ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

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
      name    = "ollama"
      image   = "ghcr.io/hotosm/osm-tagger/osm-tagger-ollama:${var.ollama_image_tag}"
      command = ["ollama", "serve"]
      cpu     = 2048
      memory  = 8192
      portMappings = [
        {
          containerPort = 11434
          hostPort      = 11434
        }
      ]
      log_configuration = {
        logdriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.osm_tagger_ollama.name
          awslogs-region        = "us-east-1" # Replace with your region
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

  # container_cpu_architecture = "ARM64"
  container_cpu_architecture = "X86_64"
  force_new_deployment       = true
  task_role_arn              = aws_iam_role.ecs_task_role.arn

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
