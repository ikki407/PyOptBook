# PuLP 4.0 移行メモ（第6章）

## 要旨

関連: [Issue #28](https://github.com/ohmsha/PyOptBook/issues/28)、[PuLP 公式移行ガイド](https://coin-or.github.io/pulp/guides/how_to_migrate_to_v4.html)。

`v4.0` ブランチでは、まず担当範囲の `6.api` を PuLP 4.0.0 に移行する。学生・車の集合、変数名、変数の範囲、6種類の制約、結果の列名・型・CSV/JSON の形式は維持する。実装中の既存コメントは変更せず、移行の説明をこの文書にまとめる。他章の移行は別ブランチで扱う。

## 環境構築

PuLP 4.0 は Python 3.12 以上が必要。従来の Python 3.7 / 3.8 環境とは分ける。

```sh
python3.12 -m venv .venv-api
. .venv-api/bin/activate
python -m pip install -r 6.api/requirements.txt
cd 6.api
python problem.py
```

Windows では `.venv-api\Scripts\activate` で有効化する。CBC は PuLP 本体に同梱されなくなったため、`pulp[cbc]==4.0.0` によって導入する。`pulp.listSolvers(onlyAvailable=True)` に `COIN_CMD` があることと、実際に小さな問題を解けることの両方を確認する。

第6章だけを移行した段階では、ルートの `requirements.txt` は変更しない。他章を含む v4 一括移行と uv への移行は、それぞれ別ブランチ・PR で進める。既存版の v3 固定と書籍への注意書き反映は別作業とする。未移行の他章を実行する場合は、PuLP 3.3.2 の別環境を使う。

## 注意すべき変更点

| 対象 | 3.x | 4.0 と本リポジトリでの対応 |
| --- | --- | --- |
| 変数の生成 | `pulp.LpVariable.dicts(...)` | `prob.add_variable_dicts(...)`。問題を作ってから、その問題に属する変数を作る。 |
| CBC | `pulp.PULP_CBC_CMD(...)` または暗黙の既定ソルバー | `pulp.COIN_CMD(...)` と CBC の別途導入。第6章では CBC を明示する。 |
| 求解の戻り値 | 整数ステータス | `stats = prob.solve(...)` は `LpSolveStats`。`stats.status`、`stats.status_str`、`stats.has_solution` を使う。 |
| 解の有無 | `status == 1` だけでは最適性と実行可能性を区別できない場合がある | 第6章は目的関数のない実行可能性問題なので `stats.has_solution` で判定する。 |
| 制約の参照 | `prob.constraints` は辞書 | `prob.constraints()` はリスト。名前で参照する場合は `prob.get_constraint_by_name(name)`。第6章の実装には該当箇所なし。 |

実行可能解がない場合は `ValueError` にステータスを含めて返す。旧コードは求解に失敗しても変数値を読み、部分的・不正な割当を結果として返し得たため、この場合だけ動作を変更する。時間制限でも実行可能解があれば利用する。HTTP のエラー形式を新設する変更は含めていないため、例外は既存の Web フレームワークのエラー処理に委ねる。

車 ID は従来どおり、車データの行順に対応する 0 始まりの連番を前提とする。入力検証や ID 仕様の拡張はこの移行の対象外。

## 出力の比較と回帰テスト

移行前のコミット `3f5c7f7cf1ac7a3793dfc7c47bb90f38d091f347` の `6.api/problem.py` を、PuLP 3.3.2 / Python 3.12.12 / CBC 2.10.3 で実行し、`tests/fixtures/api_pulp3.json` に比較基準を保存した。元コードの SHA-256、モデルの署名、実際の割当、一意解の例を記録している。基準は移行後のコードから作り直していない。

- 24人・6台のモデルについて、144変数の名前・種類・上下限、72制約の係数・向き・定数、目的関数を正規化して SHA-256 で比較する。内部のダミー変数、制約の自動命名、順序、整数/浮動小数の表記差は除く。
- 全学生がちょうど1台に割り当てられること、定員、免許、全学年、男女の条件を入力データから独立に検証する。各条件を満たせない入力も実際の CBC で確認する。
- 4人・1台の一意解は、DataFrame・CSV・JSON を移行前と完全一致で比較する。
- 複数解のある標準データでは、割当の完全一致を合否条件にしない。元の解、現在の解、車を入れ替えた別解がすべて同じ条件を満たすことを確認する。目的関数がないため、実行可能解の目的値は同一。
- Flask API、FastAPI、HTML 表示と CSV ダウンロード、入力エラー、繰り返し求解、独立した問題インスタンスを検証する。Streamlit は前処理・CSV 変換を対象とし、ブラウザー操作は対象外。
- 時間制限のステータスは、実行時間に依存する不安定なテストを避け、解あり・解なしの結果オブジェクトを使って分岐を検証する。

```sh
python -m pip install -r requirements-test.txt
python -m pytest -q
```

基準の再生成は履歴を含む checkout と PuLP 3.3.2 の別環境で `python tests/capture_api_baseline.py` を実行する。元コード自体に対するテストでは `python -m pytest -q -o filterwarnings=default tests/test_api.py` を使う。CI は Python 3.12 / 3.13 で、元コード + 3.3.2 と移行後 + 4.0.0 の両方を実行する。4.0 側では PuLP の非推奨警告をエラーにする。

ローカルの macOS arm64 では `cbcbox 2.935` の CBC 実行が終了コード -9 で失敗したため、比較には両環境で同じ CBC 2.10.3 実行ファイルを指定した。テストだけでソルバーを固定する場合は `PYOPTBOOK_CBC_PATH=/path/to/cbc python -m pytest -q` を使う。実装の CBC 選択は変更しない。別の CBC を使うアプリケーションでは `pulp.COIN_CMD(path='/path/to/cbc')` を指定できる。CBC の違いによっても複数解の選択は変わり得る。

FastAPI/Pydantic の `dict()`、pandas の HTML 文字列読込には既存の非推奨警告が残る。PuLP 以外の API 変更はこの PR に混ぜない。

## 読者向けに書籍へ追記・修正する箇所

| 箇所 | 記載内容 |
| --- | --- |
| 実行環境・インストールの説明 | 掲載時の Python 3.7 / 3.8、PuLP 2.4 と、移行版の Python 3.12 以上、PuLP 4.0、CBC 追加導入を区別する。旧コードを読む場合は PuLP 3.3.2 の環境を使う。 |
| 第6章 `CarGroupProblem._formulate` の変数定義 | `LpVariable.dicts` を `prob.add_variable_dicts` に置換したコードを掲載する。変数は問題に所属し、別の問題へ使い回せないことを説明する。 |
| 第6章 `CarGroupProblem.solve` の求解と結果取得 | `LpSolveStats` の取得、`has_solution` の確認、解がない場合に結果を出力しない処理を掲載する。 |
| 第6章の出力例・動作確認 | 車ごとの学生 ID が掲載例と異なっても、6種類の条件を満たせば正しい。完全一致が必要な例と複数解の例を区別する。 |
| 他章のステータス説明 | `pulp.LpStatus[status]` と `prob.status` は廃止。`stats.status_str` / `stats.status` を使う。許容ギャップや時間制限で停止した実行可能解は、最適性が証明された解と区別する。 |
| 他章の制約参照・配送計画 | 制約取得 API、空の数式 `LpAffineExpression.empty()`、問題間での変数共有不可、問題オブジェクトの pickle 不可を該当コードと合わせて確認する。 |

ページ番号は版ごとに異なるため、校正時に対応する節・コード掲載ページへ割り当てる。
