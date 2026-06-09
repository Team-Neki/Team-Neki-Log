locals {
  src_dir   = "${path.module}/../src"
  build_dir = "${path.module}/build"
  pkg_dir   = "${path.module}/build/pkg"
  zip_path  = "${path.module}/build/lambda.zip"

  # 코드/스키마/의존성 중 하나라도 바뀌면 재빌드 + Lambda 재배포를 트리거한다.
  # archive_file(data source)은 plan 시점에 source_dir를 읽으므로, pip로 의존성을
  # vendor해야 하는 경우 빌드 산출물이 아직 없어 사용할 수 없다. 대신 빌드를
  # null_resource(local-exec)로 수행하고, source_code_hash는 소스 입력 해시로 준다.
  source_hash = sha256(join("", [
    filesha256("${local.src_dir}/handler.py"),
    filesha256("${local.src_dir}/schemas/ga4-daily-report.v1.json"),
    filesha256("${local.src_dir}/requirements.txt"),
  ]))
}

# jsonschema(+ 네이티브 의존성 rpds-py)는 Lambda 런타임 기본 제공이 아니므로
# arm64/py3.13 대상 wheel을 vendor해 zip에 포함한다. boto3는 런타임 제공이라 제외.
resource "null_resource" "lambda_build" {
  triggers = {
    source_hash = local.source_hash
  }

  provisioner "local-exec" {
    interpreter = ["bash", "-c"]
    command     = <<-EOT
      set -euo pipefail
      rm -rf "${local.pkg_dir}" "${local.zip_path}"
      mkdir -p "${local.pkg_dir}"
      cp -R "${local.src_dir}/." "${local.pkg_dir}/"
      rm -f "${local.pkg_dir}/requirements.txt"
      python3 -m pip install \
        -r "${local.src_dir}/requirements.txt" \
        --target "${local.pkg_dir}" \
        --platform manylinux2014_aarch64 \
        --implementation cp \
        --python-version 3.13 \
        --only-binary=:all: \
        --upgrade
      find "${local.pkg_dir}" -type d -name "__pycache__" -prune -exec rm -rf {} +
      find "${local.pkg_dir}" -type f -name "*.pyc" -delete
      ( cd "${local.pkg_dir}" && zip -qr -X "../lambda.zip" . )
    EOT
  }
}

resource "aws_lambda_function" "ingest" {
  function_name                  = var.function_name
  runtime                        = "python3.13"
  architectures                  = ["arm64"]
  memory_size                    = 256
  timeout                        = 10
  reserved_concurrent_executions = 2
  handler                        = "handler.lambda_handler"
  role                           = aws_iam_role.lambda.arn

  filename         = local.zip_path
  source_code_hash = local.source_hash

  environment {
    variables = {
      S3_BUCKET                = aws_s3_bucket.main.id
      S3_PREFIX                = "aggregation"
      REPORT_DATE_MAX_AGE_DAYS = tostring(var.report_date_max_age_days)
      LOG_LEVEL                = "INFO"
    }
  }

  depends_on = [
    null_resource.lambda_build,
    aws_cloudwatch_log_group.lambda,
    aws_iam_role_policy.lambda,
  ]
}
