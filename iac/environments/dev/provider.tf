terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # NOTE: may want to implement a lock table
  backend "s3" {
    bucket = "hotosm-terraform"
    key    = "osm-tagger/dev/terraform.tfstate"
    region = "us-east-1"

    # dynamodb_table = "osm-tagger-terraform-state-lock"
    encrypt = true
  }
}

provider "aws" {
  region = "us-east-1"

  default_tags {
    tags = {
      project     = "osm-tagger"
      environment = "dev"
    }
  }
}
