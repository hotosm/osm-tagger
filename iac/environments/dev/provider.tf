terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # TODO: set up backend for terraform state
  # NOTE: may want to implement a lock table
  # backend "s3" {
  #   bucket = "osm-tagger-terraform-state"
  #   key    = "dev/terraform.tfstate"
  #   region = "us-east-1"

  #   dynamodb_table = "osm-tagger-terraform-state-lock"
  #   encrypt        = true
  # }
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
