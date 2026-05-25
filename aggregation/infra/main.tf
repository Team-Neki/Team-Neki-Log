terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # NOTE: 초기 배포 시 backend S3 버킷이 아직 없으므로 우선 local state로 시작.
  # 첫 apply로 버킷이 생성된 뒤 아래 backend를 활성화하고
  # `terraform init -migrate-state` 로 state를 옮긴다.
  #
  # backend "s3" {
  #   bucket = "team-neki-log-production"
  #   key    = "terraform/state/aggregation.tfstate"
  #   region = "ap-northeast-2"
  # }
}

provider "aws" {
  region = var.aws_region
}
