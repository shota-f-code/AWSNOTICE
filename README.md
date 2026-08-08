# AWS Health 通知パイプライン (AWSNOTICE)

## 1. 概要
本プロジェクトは、AWS Health で発生した各種イベント（メンテナンス、障害情報等）を検知し、EventBridge および Lambda を介して Slack および Backlog へ自動通知するパイプラインを AWS CDK を用いてコード化（IaC化）するものである。

手動構築された既存の通知検証環境をベースに、最小権限の IAM ポリシーや AWS Secrets Manager を用いた安全な Webhook URL / API キー管理を組み込んだ再利用可能なインフラストラクチャとして構築する。

---

## 2. アーキテクチャ構成
1. **AWS Health**: イベント（障害・計画メンテナンス等）の発生源
2. **Amazon EventBridge**: AWS Health イベントを検知しターゲット（Lambda）へルーティング
3. **AWS Lambda**: イベントメッセージを整形し、外部サービスへ API/Webhook 経由で送信
4. **AWS Secrets Manager**: Slack Webhook URL や Backlog API キー等の機密情報を安全に保持
5. **Slack / Backlog**: 最終的な通知・課題起票先

---

## 3. パッケージ・環境管理 (`uv`)

本プロジェクトでは、高速かつ厳密な依存関係管理を実現するため、Python パッケージ管理ツールとして **`uv`** を採用している。

### `uv` 採用の理由
* **高速な動作**: Rust 製であり、既存ツール（Poetry 等）と比較して依存解決およびパッケージインストールが非常に高速である。
* **環境の一元管理**: `pyproject.toml` および `uv.lock` により、決定論的で再現性の高い仮想環境構築が可能となる。
* **標準規格への準拠**: Python 標準規格である `pyproject.toml` を中心にプロジェクトを管理する。

### 基本コマンド

```bash
# 仮想環境のセットアップおよび依存関係の同期
uv sync

# パッケージの追加
uv add <package_name>

# CDK コマンドの実行 (cdk.json 経由で uv run が使用される)
cdk synth
cdk diff
cdk deploy
```