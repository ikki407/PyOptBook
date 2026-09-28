# PuLP 3.x 固定と書籍への注意書き候補

## 暫定対応の要旨

`v3.0` は `main` から作成し、`requirements.txt` の PuLP だけを最新の安定した 3.x である `pulp==3.3.2` に固定する（2026年9月29日確認）。ソースコードとノートブックは変更しない。バージョン指定のないインストールで PuLP 4 が入り、掲載コードの変数定義やステータス参照が失敗することを防ぐ。

関連: [Issue #28](https://github.com/ohmsha/PyOptBook/issues/28)、[PuLP 3.3.2](https://pypi.org/project/PuLP/3.3.2/)、[公式 v4 移行ガイド](https://coin-or.github.io/pulp/guides/how_to_migrate_to_v4.html)。

この固定は PuLP に限る。他ライブラリや OS を含む掲載時の環境全体を再現するものではない。PuLP 3.3.2 の対応 Python は **3.10 以上**であり、掲載時の Python 3.7 / 3.8 にそのまま導入できるわけではない。今回の動作確認は Python 3.12.12 / PuLP 3.3.2 / CBC 2.10.3 で行う。

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -c "import pulp; print(pulp.__version__)"
```

Windows の仮想環境の有効化は `.venv\Scripts\activate` とする。表示が `3.3.2` であることを確認する。既存環境の PuLP だけを戻す場合は `python -m pip install "pulp==3.3.2"` を使う。

## 書籍へ転記する注意書き案

以下は校正用の候補。実際の掲載位置とページ番号は各版の組版時に確認する。

### 実行環境の表・インストール手順の直後

> PuLP はバージョン 4.0 で API が変更されました。本書に掲載したコードの PuLP の書き方を利用する場合は、PuLP 3.3.2 をインストールしてください。サポートサイトの `v3.0` ブランチでは、このバージョンを指定しています。PuLP 3.3.2 には Python 3.10 以上が必要です。本文の実行環境表は刊行時の情報であることに注意してください。

```sh
python -m pip install "pulp==3.3.2"
```

### 第2章・最初の変数定義の説明

> 本文の `pulp.LpVariable(...)` や `pulp.LpVariable.dicts(...)` は PuLP 3.x 以前の書き方です。PuLP 4.0 では先に問題 `prob` を作成し、`prob.add_variable(...)` や `prob.add_variable_dicts(...)` で変数を定義します。変数は作成した問題に所属するため、別の問題にそのまま使い回すことはできません。

### 第2章・最初の求解とステータス表示の説明

> PuLP 4.0 の `solve()` は整数ではなく、求解情報を持つ `LpSolveStats` を返します。`stats = prob.solve()` とした場合、ステータス表示には `stats.status_str`、最適性の判定には `stats.status == pulp.LpSolveStatus.Optimal` を使います。本文の `pulp.LpStatus[status]` や `prob.status` は PuLP 4.0 では使用できません。

### 第5章・CBC の設定と許容ギャップの説明

> PuLP 4.0 では CBC は本体に同梱されず、`PULP_CBC_CMD` も廃止されています。`python -m pip install "pulp[cbc]==4.0.0"` で CBC を追加し、`pulp.COIN_CMD(...)` を使ってください。許容ギャップや時間制限で終了した場合、実行可能な解が得られていても最適性が証明されているとは限りません。`stats.has_solution` で解の有無を確認し、終了理由と最適性を区別してください。

### 第3章・第6章の割当結果、第5章の配送経路の出力例

> この問題では、同じ目的関数値を持つ解が複数存在することがあります。PuLP やソルバーのバージョン、探索順によって、具体的な割当や配送経路が掲載例と異なる場合があります。結果の ID や並びだけでなく、すべての制約が満たされていることと、目的関数値を確認してください。第6章は目的関数を設定しないため、条件を満たす割当はいずれも解として扱います。

### サポートサイト案内・最新版を使う読者向け

> 掲載時の PuLP の書き方を使う場合は `v3.0` ブランチを参照してください。PuLP 4.0 へ移行する場合は、移行版のコードと移行メモを参照し、Python 3.12 以上の別環境を作成してください。旧版のコードと新版のライブラリを混在させないようにしてください。

uv 版を案内する場合の追記候補:

> uv 版では `pyproject.toml` と `uv.lock` で実行環境を管理します。uv を使用しない場合にも、同じロックファイルから生成した `requirements.txt` を使って pip で導入できます。詳細なコマンドは該当ブランチの README を参照してください。

## 校正時のチェック対象

実行環境表、インストール例、第2章の変数生成・ステータス表示、第5章の CBC・許容ギャップ、第6章の解の有無の確認、各章の出力例を確認する。v4 のコードへ差し替える場合は、注意書きだけでなく対応するコード掲載箇所もまとめて更新する。
