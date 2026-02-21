# Detailed Tagging Tool

このリポジトリは、映像フレームに対して階層化されたタグ付けを行うためのデスクトップアプリケーションです。簡易タグ（CSV）を検索して該当フレームへジャンプし、3段階の階層タグを効率的に付与できます。出力は正規化された CSV として保存され、位置情報や簡易タグの内容もマージされます。

## インストール

Python 3.11 以降が必要です。プロジェクトルートには依存関係を列挙した `requirements.txt` があります。

```bash
$ python -m venv .venv
$ source .venv/bin/activate        # Windows の場合は `.venv\Scripts\activate`
$ pip install -r detailed_tagger/requirements.txt
```

ffprobe を利用した可変フレームレート (VFR) 動画の厳密なフレームマッピング機能を使用する場合は、システムに FFmpeg/ffprobe をインストールしてパスが通っている必要があります。インストールされていない環境では平均 FPS による近似モードで動作します。

## 実行方法

アプリ本体は `app.main` モジュールです。パッケージとして実行することで相対インポートが正しく機能します。

```bash
$ python -m detailed_tagger.app.main
```

起動後、上部ペインから親フォルダを読み込み、簡易タグ CSV やタグ設定 JSON を選択して作業を開始します。タグ設定ファイルの例は `configs/tag_config_sample.json` にあります。

## タグ設定ファイルの CSV→JSON 変換

`formats/tag_config_converter.py` は、タグ設定を CSV 形式から JSON 形式へ変換するためのコマンドラインツールです。CSV は以下の列を持つ必要があります。

| 列名    | 説明                          |
|---------|-------------------------------|
| `lv1`   | 第1階層のタブ名               |
| `lv2`   | 第2階層のボタン名             |
| `lv3`   | 第3階層の詳細タグ名           |
| `shortcut` (任意) | その詳細タグに割り当てるショートカットキー |

使用方法:

```bash
$ python -m detailed_tagger.formats.tag_config_converter input.csv output.json
```

出力された JSON をタグ設定ファイルとして読み込むと、アプリ上で階層タグ UI が構築され、ショートカットキーが自動的に登録されます。

## ショートカット設定と競合検出

タグ設定 JSON には、各詳細タグに対するショートカットと、グローバル操作（フレーム送り、次/前ファイル、エクスポート、Undo など）に対するショートカットを定義できます。読み込み時に同じキーが複数のアクションやタグに割り当てられていると、ステータスバーに警告が表示されます。競合を解消するには、タグ設定 JSON 内のショートカットを修正してください。

## 単一ファイルへのパッケージング

このアプリケーションは PyQt6 を使用しており、PyInstaller などで単一の実行ファイルとして配布することができます。以下は基本的な手順の例です。

```bash
$ pip install pyinstaller
$ pyinstaller --name DetailedTagger --onefile --noconsole --add-data "detailed_tagger/configs:configs" -m detailed_tagger.app.main
```

`--add-data` オプションは、タグ設定サンプルなどのリソースをバンドルするために使用します。プラットフォームに応じてパスの区切り記号を調整してください（Windows では `;`、Unix 系では `:`）。

ビルドが完了すると、`dist/DetailedTagger`（Windows では `dist\DetailedTagger.exe`）に単一ファイルが生成されます。実行ファイルと同じディレクトリにフォルダを置かないとタグ設定ファイルが見つからない場合があるため、必要に応じて `configs` ディレクトリを同梱してください。

## ライセンス

このプロジェクトは社内利用を想定しており、ライセンスは指定されていません。外部への公開を行う場合は適切なライセンスを設定してください。# detailed_tagger
