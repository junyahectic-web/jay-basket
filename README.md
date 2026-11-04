# 藤沢市 バスケ空き検索

藤沢市公共施設予約システムで、バスケットボール・ミニバスケットボールができる室場の空き枠を検索するページです。
期間（今日から何日間）、火曜・木曜の時間帯、土日祝日の時間帯、秋葉台・秩父宮のサブアリーナを含めるかを画面で指定します。

## しくみ（すべて無料）

- **GitHub Actions** が1時間ごとに `scrape.py`（Playwright）を動かし、今日から120日分の空き枠を `docs/data.json` に保存する。
- **GitHub Pages** が `docs/index.html`（検索画面）を公開する。検索は画面の中で行うので、開くとすぐ結果が出る。
- 公開リポジトリなら GitHub Actions・GitHub Pages ともに無料（クレジットカードの登録も不要）。

## 公開する手順

1. https://github.com/signup で GitHub のアカウントを作る（無料プランのまま）。
2. https://github.com/new でリポジトリを作る。
   - Repository name: `fujisawa-basket`（好きな名前でよい）
   - **Public** を選ぶ（Private だと GitHub Pages が無料で使えない）
   - そのほかは何も選ばずに「Create repository」
3. できた画面の「uploading an existing file」をクリックし、このフォルダの次のものをドラッグ＆ドロップして
   「Commit changes」を押す。
   - `scrape.py` / `requirements.txt` / `README.md` / `docs` フォルダ（中に `index.html` と `data.json`）
4. リポジトリの「Settings」→ 左の「Pages」→「Build and deployment」の Source を **GitHub Actions** に変える。
5. リポジトリのトップに戻り「Add file」→「Create new file」を押す。
   - ファイル名の欄に `.github/workflows/update.yml` と入力する（`/` を打つとフォルダになる）
   - 本文に、このフォルダの `.github/workflows/update.yml` の中身をすべて貼り付けて「Commit changes」
   - ※ `.github` フォルダは Mac の Finder では隠れていてドラッグできないため、この方法で作る
6. 「Actions」タブで「空き状況の更新」が緑のチェックになるまで待つ（5分ほど）。
7. `https://<ユーザー名>.github.io/fujisawa-basket/` が検索ページのURL。これを友人に送る。
   スマホでは、ブラウザの「ホーム画面に追加」をするとアプリのように開ける。

## 注意

- 空き状況は1時間ごとの更新なので、予約の前に予約システムで最新の状況を確認する。
  3時間以上更新されていないときは、画面に注意書きが出る。
- GitHub の混雑で、自動実行が数分〜数十分遅れることがある。すぐ更新したいときは
  「Actions」→「空き状況の更新」→「Run workflow」で手動実行できる。
- 自動実行が止まったとき（Actions に「disabled」と出たとき）は、同じ画面の「Enable workflow」で再開する。

## 手元の Mac で動かす

```bash
cd fujisawa_akijoho/basket_pages
../../chigasaki_akijoho/.venv/bin/python scrape.py
../../chigasaki_akijoho/.venv/bin/python -m http.server 8060 --directory docs
```

ブラウザで http://127.0.0.1:8060 を開く。
