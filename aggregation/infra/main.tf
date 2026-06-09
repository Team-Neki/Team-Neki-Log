terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # State는 첫 apply로 생성된 버킷의 terraform/state/ prefix에 self-host한다.
  # DynamoDB 잠금 미사용 (단일 운영자 가정, LLD §9.3).
  backend "s3" {
    bucket = "team-neki-log-production"
    key    = "terraform/state/aggregation.tfstate"
    region = "ap-northeast-2"
  }
}

provider "aws" {
  region = var.aws_region
}
