data "aws_iam_policy_document" "media_signer" {
  statement {
    sid = "AllowDirectUploadSigningTargets"

    actions = [
      "s3:PutObject",
      "s3:AbortMultipartUpload",
    ]

    resources = ["${var.media_bucket_arn}/workspaces/*"]
  }

  statement {
    sid = "AllowKmsForMediaObjects"

    actions = [
      "kms:Decrypt",
      "kms:Encrypt",
      "kms:GenerateDataKey",
    ]

    resources = [var.kms_key_arn]
  }
}

resource "aws_iam_policy" "media_signer" {
  name        = "${var.name_prefix}-media-signer"
  description = "Allows the SocialOS API to sign direct media uploads."
  policy      = data.aws_iam_policy_document.media_signer.json
  tags        = var.tags
}
