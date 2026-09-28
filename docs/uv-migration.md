# uv 移行メモ

## 要旨

`codex/v4.0-uv` は他章の PuLP 4 移行ブランチを土台とし、環境構築・依存更新・テスト実行を uv に統一する。数理モデルのコードはこの段階では変更しない。初心者向けの pip 用 requirements も残し、同じロックファイルから生成する。

Python 3.12 / 3.13 を対象とし、`.python-version` は標準の 3.12 を指定する。`pyproject.toml` の対応範囲は `>=3.12,<3.14`。この範囲は PuLP 自体の対応範囲ではなく、本リポジトリで検証する環境の範囲である。

| ファイル | 役割 |
| --- | --- |
| `pyproject.toml` | 依存の宣言。共通部分は NumPy・pandas・PuLP。`api`、`notebooks`、`dev`、`alternatives` の各グループに章や用途ごとの依存をまとめる。 |
| `uv.lock` | 推移的な依存も含めたバージョンと配布物の固定。Git に保存する。 |
| `.python-version` | 通常使う Python の系列。 |
| `requirements.txt` | 共通部分 + API + ノートブック。テスト依存を含めない。 |
| `6.api/requirements.txt` | 共通部分 + API。第6章だけに必要な依存。 |
| `requirements-test.txt` | 通常実行と回帰テストに必要な依存。 |
| `requirements-alternatives.txt` | 通常実行 + python-mip / CVXPY の比較例。 |

既定の `uv sync` は API・ノートブック・開発用の各グループを導入する。比較例の追加ライブラリは必要に応じて選択する。書籍用のファイル構成を維持するため、Python パッケージとしてのビルド・インストールは行わない。

## 利用方法

uv 0.9.7 以上を使用する。CI の uv は再現性のため 0.9.7 に固定する。[公式インストール手順](https://docs.astral.sh/uv/getting-started/installation/)を参照。

```sh
uv sync --locked
uv run --locked jupyter notebook
uv run --locked pytest -q
```

第6章だけを導入する場合:

```sh
uv sync --locked --no-default-groups --group api
cd 6.api
uv run --locked --no-default-groups --group api python problem.py
uv run --locked --no-default-groups --group api uvicorn api_fastapi:app
```

`uv run` でも同じグループ指定を使う。省略すると既定のグループが再び導入される。入力データが章ごとの相対パスにあるため、スクリプトはその章のディレクトリから実行する。

比較例も導入する場合:

```sh
uv sync --locked --group alternatives
uv run --locked --group alternatives jupyter notebook
```

pip を使う場合は README の手順で仮想環境を作り、利用範囲に対応する requirements をインストールする。ロック由来のファイルにも OS や Python バージョンに応じた条件が含まれるため、行を手で削除しない。

## 依存を更新する手順

```sh
uv add --group notebooks パッケージ名
uv lock
python scripts/export_requirements.py
uv sync --locked
uv run --locked pytest -q
```

既存の依存を更新する場合は `uv lock --upgrade-package パッケージ名` を使う。PuLP は移行検証した `4.0.0` に固定しているため、別の版に上げる際は `pyproject.toml` の指定も更新し、回帰テストを実行する。

requirements は手編集せず、`scripts/export_requirements.py` で4ファイルを再生成する。`python scripts/export_requirements.py --check` は、ロックの不整合・出力ファイルとの差分があれば失敗する。CI でも `uv lock --check` とこの検査を実行する。`uv export --locked` を使用し、古いロックを無条件で出力する `--frozen` は使わない。

## 検証と注意点

CI は Python 3.12 / 3.13 で、uv のロックから導入する経路と生成した requirements を pip で導入する経路の両方で回帰テストを実行する。旧版の第6章 + PuLP 3.3.2 の回帰テストも残す。比較用グループは追加導入と主要モジュールの import を確認し、python-mip / CVXPY 自体の全出力比較は対象外とする。

CBC の環境固有の実行問題と数値比較の範囲は [第6章のメモ](pulp-v4-migration.md)と[他章のメモ](pulp-v4-notebooks.md)を参照。依存の固定で複数最適解の選択まで保証するものではない。

macOS arm64 の `cbcbox 2.935` では、配布された `libgfortran`・`libquadmath`・`libgcc_s` のコード署名検査が失敗し、CBC が終了コード -9 になることを確認した。本体の数理モデルとは別の配布物の問題である。検証には独立した CBC 実行ファイルを指定している。必要に応じて利用可能な CBC を `COIN_CMD(path=...)` で指定する。グローバル環境や OS のセキュリティ設定は変更しない。

## 書籍に記載する候補

> 移行版のサンプルコードでは、uv で Python とライブラリの実行環境を管理します。リポジトリのルートで `uv sync --locked` を実行すると、`uv.lock` に記録したライブラリが導入されます。ノートブックは `uv run --locked jupyter notebook` で起動できます。

> uv を使わない場合は、Python 3.12 または 3.13 の仮想環境を作り、`python -m pip install -r requirements.txt` を実行してください。このファイルも `uv.lock` から生成しているため、同じ環境向けには同じライブラリのバージョンを使用します。

> 第6章のスクリプトは `6.api` ディレクトリに移動して実行します。python-mip や CVXPY を使った比較例には追加ライブラリが必要です。導入方法は README を参照してください。

実行環境・インストール手順・各章の実行例・サポートサイト案内への追記候補とし、実際の校正は別作業とする。
