# jageocoder-server

このプログラムは、日本語住所ジオコーダー jageocoder を利用して
住所文字列を解析したり CSV に含まれる住所表記に経緯度を追加するといった
処理を実現するウェブアプリケーションです。

データファイルをダウンロードしておけば、スタンドアロンで動作します。
ネットワークが利用できない災害時、セキュリティ上の理由で外部サービスを
利用できない環境、または外部に送信できないデータをローカル環境で
処理したい場合などに利用できます。

また、サブネット内で他のアプリケーションから利用できる WebAPI 
サーバ機能も提供します。

# 利用手順

- [GitHub](https://github.com/t-sagara/jageocoder-server) から最新の
  コードを clone, または ZIP ファイルをダウンロードしてください。
- 任意の場所に展開し、ターミナル (Windows の場合は PowerShell) で
  この README.md ファイルがあるディレクトリを開いてください。

## Docker を利用する場合

- [Docker Engine](https://docs.docker.com/engine/) または
  [Docker Desktop](https://www.docker.com/products/docker-desktop/) が必要です。

- インストールする辞書をセットします。

    - [データファイル一覧](https://www.info-proto.com/static/jageocoder/latest/v2/)
      からダウンロードし、`data/` に配置してください。
    - data ディレクトリには他の zip ファイルは置かないでください。

- サーバ設定

    `docker-compose.yml` の `environment:` 以下の行で
    サーバの設定を行うことができます。

    - `SITE_MESSAGE`: サーバに表示する文字列を設定できます。
    - `LAN_MODE`: 1 にすると、地図表示のために地理院地図サーバに
      アクセスするといった外部ネットワークへの通信を行いません。
    - `BUILD_RTREE`: 1 にすると、リバースジオコーディング機能に
      必要なインデックスを初回起動時に構築します。

- 以下の手順でコンテナを作成し、実行します。

        $ docker compose build
        $ docker compose up -d

    初回インストール時には辞書のインストールを行います。

    所要時間は辞書のサイズやコンピュータの性能にもよりますが、
    たとえば全国の住居表示レベルの場合は 1 分間程度かかります。

    `BUILD_RTREE` を 1 にした場合、リバースジオコーディング用の
    R-tree インデックスも構築します。こちらは 10 分間以上かかります。

    `data/init.log` に進捗状況が出力されますので、 `All done.` と
    表示されるまでのんびりお待ちください。

- ブラウザで `http://localhost:5000/` にアクセスしてご利用ください。

- 作業が終わったらコンテナを停止します。

        $ docker compose down

    インストールした辞書データは Docker Volume に保存されているので、
    二回目以降の実行時はコンテナを起動すればすぐに利用できます。

        $ docker compose up -d

- もう利用しない場合はアンインストールしてください。

    完全にアンインストールするには Volume も削除してください。

        $ docker compose down -v
        $ docker system prune

## Linux の場合

- Python3.8 以上がインストールされている環境が必要です。

    他の Python アプリケーションとの競合を防ぐため、
    `venv` 等で仮想環境を作成することをお勧めします。

        $ python -m venv .venv
        $ .venv/bin/activate

- Python パッケージをインストールします。

        $ python -m pip install -r requrements.txt

- 辞書データファイルをダウンロード・インストールします。

    サーバ上の他のアプリケーションで辞書データをインストール済みの場合、
    辞書がインストールされているディレクトリを環境変数 `JAGEOCODER_DB2_DIR` に
    セットしてください。

    インストールされていない場合は [データファイル一覧](https://www.info-proto.com/static/jageocoder/latest/v2/)
    から適切なデータファイルをダウンロードして、次のコマンドでインストールしてください。

        $ python -m jageocoder install-dictionary <データファイルzip>
        (例)
        $ python -m jageocoder install-dictionary jukyo_all_v20.zip

    リバースジオコーディング機能を利用したい場合は、
    R-tree インデックスを構築しておく必要があります。
    以下のコマンドを実行してインデックスを構築してください。

        $ python -m jageocoder reverse 140.0 35.0

    サーバを起動中に R-tree インデックスを構築した場合、
    一度サーバを Ctrl+C で停止して、再度起動してください。

- サーバを起動します。

        $ python server/run_waitress.py

    サーバのバインドアドレス (0.0.0.0) やポート (5000) を変更したい場合は
    環境変数 `JAGEOCODER_SERVER_HOST` および `JAGEOCODER_SERVER_PORT` を
    指定して実行してください。

        $ JAGEOCODER_SERVER_PORT=8000 python server/run_waitress.py

- ブラウザで `http://<server>:5000/` にアクセスしてください。

    ポートを変更した場合はそのポート番号を指定してください。

- 作業が終わったらサーバを停止します。

    実行中のプロセスを Ctrl+C で終了します。

## 著作者表示

* **相良 毅** - [Info-proto Co.,Ltd.](https://www.info-proto.com/)

## ライセンス

* このプログラムは [the MIT License](https://opensource.org/licenses/mit-license.php)
  に従って自由にインストール・利用が可能です。

* ただし住所データベースについては、データ提供元による利用条件があります。

## 関連情報

* ジオコーダー jageocoder および住所データベースについては
  https://t-sagara.github.io/jageocoder/ を参照してください。
